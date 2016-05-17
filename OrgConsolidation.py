# -*- coding: utf-8 -*-

# ########################## Copyrights and license ############################
#                                                                              #
# Copyright 2016 David Roegiers <david.roegiers@gmail.com>                     #
#                                                                              #
# This file is part of the author's master thesis on OSS research :            #
# https://github.com/droegier/ThesisOSS                                        #
#                                                                              #
# This script is free software: you can redistribute it and/or modify it under #
# the terms of the GNU Lesser General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)    #
# any later version.                                                           #
#                                                                              #
# This script is based on the PyGithub library v 1.26.0                        #
# http://pygithub.github.io/PyGithub/v1/introduction.html                      #
#                                                                              #
# ##############################################################################

"""
This is the main file. It illustrates how repositories are collected, stored, and managed from the GitHub API v3,
using the PyGitHub library. Additionally, it displays the organisations and repositories that were gathered for
the analysis of the research paper.
"""

import time
import ssl
import os
import xml.etree.ElementTree as ET
import Organisation
import csv
import sys

class OrgConsolidation(object):

    def __init__(self):
        pass

    def __del__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass

    def getTimeBetweenActions(self):
        outfile = 'data/' + 'inter_action_time.csv'

        #delete file if it exists
        try:
            os.remove(outfile)
        except OSError:
            pass

        with open(outfile, 'w') as csvfile:
            csvwrite = csv.writer(csvfile)

            subdirs = [x[0] for x in os.walk('data')]

            subdirs = [ name for name in os.listdir('data') if os.path.isdir(os.path.join('data', name)) ]
            for subdir in subdirs:
                rep = subdir
                print 'organisation : ' + subdir
                if os.path.exists('data/' + subdir + '/' + 'participants.xml'):
                    org_tree = ET.parse('data/' + subdir + '/' + 'participants.xml')
                else:
                    continue
                org_root = org_tree.getroot()
                for participant in org_root:
                    list = []
                    for period in participant:
                        list.append(int(period.get('date')))
                    list = sorted(list)
                    for j in range(1,len(list)):
                        r = int(str(list[j-1])[0:4])
                        if r < 2005:
                            pass
                        else:
                            diff = (int(str(list[j])[0:4])-int(str(list[j-1])[0:4]))*52+int(str(list[j])[4:])-int(str(list[j-1])[4:])
                        if diff > 700:
                            pass
                        csvwrite.writerow([diff])
        print "done"
        return True

    #TODO this function is nowhere yet
    def gatherAllActions(self):
        outfile = 'data/' + 'everything.csv'

        #delete file if it exists
        try:
            os.remove(outfile)
        except OSError:
            pass

        with open(outfile, 'w') as csvfile:
            csvwrite = csv.writer(csvfile)
            subdirs = [ name for name in os.listdir('data') if os.path.isdir(os.path.join('data', name)) ]
            for subdir in subdirs:
                pass
        print "done"
        return True


