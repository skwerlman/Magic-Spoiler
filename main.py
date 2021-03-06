# -*- coding: utf-8 -*-
import spoilers
import os
import commentjson
import json
import io
import sys

presets = {
    "isfullspoil": False, # when full spoil comes around, we only want to use WOTC images
    "includeMasterpieces": True, # if the set has masterpieces, let's get those too
    "oldRSS": False, # maybe MTGS hasn't updated their spoiler.rss but new cards have leaked
    "split_cards": {
        "Grind": "Dust"
    },
    "siteorder": ['scryfall','mtgs','mythicspoiler'], # if we want to use one site before another for card data TODO
    "imageorder": ['wotc','scryfall','mtgs','mythicspoiler'], # prioritize images from certain sources
    "useexclusively": '', # if we *only* want to use one site TODO
    "dumpXML": False, # let travis print XML for testing
    "scryfallComparison": False #if we want to debug compare scryfall to other sources, enable
}

try:
    with open('set_info') as data_file:
        setinfos = commentjson.load(data_file)
except Exception as ex:
    print "Unable to load file: set_info\nException information:\n" + str(ex.args) + \
          "\nUnable to load file: set_info"
    sys.exit("Unable to load file: set_info")
try:
    with open('cards_manual') as data_file:
        manual_sets = json.load(data_file)
except Exception as ex:
    print "Unable to load file: cards_manual\nException information:\n" + str(ex.args) + \
          "\nUnable to load file: cards_manual"
    sys.exit("Unable to load file: cards_manual")
try:
    with open('cards_corrections') as data_file:
        card_corrections = commentjson.load(data_file)
except Exception as ex:
    print "Unable to load file: cards_corrections\nException information:\n" + str(ex.args) + \
          "\nUnable to load file: cards_corrections"
    sys.exit("Unable to load file: cards_corrections")
try:
    with open('cards_delete') as data_file:
        delete_cards = commentjson.load(data_file)
except Exception as ex:
    print "Unable to load file: cards_delete\nException information:\n" + str(ex.args) + \
          "\nUnable to load file: cards_delete"
    sys.exit("Unable to load file: cards_delete")

errorlog = []

#TODO insert configparser to add config.ini file

def parseargs():
    for argument in sys.argv:
        for preset in presets:
            if argument.split('=')[0].lower().replace('-','') == preset.lower():
                argvalue = argument.split('=')[1]
                if argvalue in ['true','True','T','t']:
                    argvalue = True
                elif argvalue in ['false','False','F','f']:
                    argvalue = False
                presets[preset] = argvalue
                print "Setting preset " + preset + " to value " + str(argvalue)

def save_allsets(AllSets):
    #TODO Create AllSets.json for Oracle
    print ""

def save_masterpieces(masterpieces, setinfo):
    with open('out/' + setinfo['masterpieces']['setname'] + '.json', 'w') as outfile:
        json.dump(masterpieces, outfile, sort_keys=True, indent=2, separators=(',', ': '))

def save_setjson(mtgs, filename):
    with io.open('out/' + filename + '.json', 'w', encoding='utf8') as json_file:
        data = json.dumps(mtgs, ensure_ascii=False, encoding='utf8', indent=2, sort_keys=True, separators=(',',':'))
        json_file.write(unicode(data))

def save_errorlog(errorlog):
    with open('out/errors.json', 'w') as outfile:
        json.dump(errorlog, outfile, sort_keys=True, indent=2, separators=(',', ': '))

def save_xml(xmlstring, outfile):
    if os.path.exists(outfile):
        append_or_write = 'w'
    else:
        append_or_write = 'w'
    with open(outfile,append_or_write) as xmlfile:
        xmlfile.write(xmlstring.encode('utf-8'))

if __name__ == '__main__':
    parseargs()
    AllSets = spoilers.get_allsets() #get AllSets from mtgjson
    combinedjson = {}
    for setinfo in setinfos:
        if presets['oldRSS'] or 'noRSS' in setinfo and setinfo['noRSS']:
            mtgs = { "cards":[] }
        else:
            mtgs = spoilers.scrape_mtgs('http://www.mtgsalvation.com/spoilers.rss') #scrape mtgs rss feed
            [mtgs, split_cards] = spoilers.parse_mtgs(mtgs, [], [], [], presets['split_cards']) #parse spoilers into mtgjson format
        mtgs = spoilers.correct_cards(mtgs, manual_sets[setinfo['setname']]['cards'], card_corrections, delete_cards) #fix using the fixfiles
        scryfall = spoilers.get_scryfall('https://api.scryfall.com/cards/search?q=++e:' + setinfo['setname'].lower())
        mtgjson = spoilers.get_image_urls(mtgs, presets['isfullspoil'], setinfo['setname'], setinfo['setlongname'], setinfo['setsize'], setinfo) #get images
        if presets['scryfallComparison']:
            mtgjson = spoilers.smash_mtgs_scryfall(mtgs, scryfall)
        [mtgjson, errors] = spoilers.error_check(mtgjson, card_corrections) #check for errors where possible
        errorlog += errors
        spoilers.write_xml(mtgjson, setinfo['setname'], setinfo['setlongname'], setinfo['setreleasedate'])
        #save_xml(spoilers.pretty_xml(setinfo['setname']), 'out/spoiler.xml')
        mtgjson = spoilers.add_headers(mtgjson, setinfo)
        AllSets = spoilers.make_allsets(AllSets, mtgjson, setinfo['setname'])
        if 'masterpieces' in setinfo: #repeat all of the above for masterpieces
            #masterpieces aren't in the rss feed, so for the new cards, we'll go to their individual pages on mtgs
            #old cards will get their infos copied from mtgjson (including fields that may not apply like 'artist')
            #the images will still come from mtgs
            masterpieces = spoilers.make_masterpieces(setinfo['masterpieces'], AllSets, mtgjson)
            [masterpieces, errors] = spoilers.error_check(masterpieces)
            errorlog += errors
            spoilers.write_xml(masterpieces, setinfo['masterpieces']['setname'], setinfo['masterpieces']['setlongname'], setinfo['masterpieces']['setreleasedate'])
            AllSets = spoilers.make_allsets(AllSets, masterpieces, setinfo['masterpieces']['setname'])
            save_masterpieces(masterpieces, setinfo)
            combinedjson[setinfo['masterpieces']['setname']] = masterpieces
        save_setjson(mtgjson, setinfo['setname'])
        combinedjson[setinfo['setname']] = mtgjson
    save_setjson(combinedjson, 'spoiler')
    spoilers.write_combined_xml(combinedjson, setinfos)
    save_xml(spoilers.pretty_xml('out/spoiler.xml'), 'out/spoiler.xml')
    errorlog = spoilers.remove_corrected_errors(errorlog, card_corrections)
    save_errorlog(errorlog)
    #save_allsets(AllSets)
    #save_setjson(mtgjson)
    if presets['dumpXML']:
        print '<!----- DUMPING SPOILER.XML -----!>'
        with open('out/spoiler.xml', 'r') as xmlfile:
            print xmlfile.read()
        print '<!-----    END XML DUMP     -----!>'
        if errorlog != {}:
            print '//----- DUMPING ERROR LOG -----'
            print json.dumps(errorlog, ensure_ascii=False, encoding='utf8', indent=2, sort_keys=True, separators=(',',':'))
            print '//-----   END ERROR LOG   -----'
        else:
            print "No Detected Errors!"
