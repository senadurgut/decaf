#!/usr/bin/env python
from optparse import OptionParser
import os
parser = OptionParser()
parser.add_option('-a', '--analysis', help='analysis', dest='analysis', default='darkhiggs')
parser.add_option('-y', '--year', help='year', dest='year', default='')
parser.add_option('-m', '--mass', help='mass', dest='mass', default='')
parser.add_option('-g', '--category', help='category', dest='category', default='')
(options, args) = parser.parse_args()
command='combineCards.py '
if options.analysis == 'darkhiggs':
    for year in ['2016','2017','2018']:
        for mass in ['mass0','mass1','mass2','mass3','mass4']:
            for category in ['monojet','monohs']:
                if options.year and options.year not in year: continue
                if options.mass and options.mass not in mass: continue
                if options.category and options.category in category: continue
                for filename in os.listdir('datacards/'+options.analysis+year+'/'+mass):
                    if '.txt' not in filename: continue
                    if category not in filename: continue
                    command=command+filename.split(".")[0]+'=datacards/'+options.analysis+year+'/'+mass+'/'+filename+' '
    command=command+' > datacards/'+options.analysis+options.year+options.mass+options.category+'.txt'
    os.system(command)
