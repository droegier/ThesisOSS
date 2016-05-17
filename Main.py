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

import Repository
import OrgConsolidation
import github
import time
import ssl
import os
import Organisation
import csv
import sys

def gatherData(org):

    pass

if __name__ == '__main__':

    # These lists are used to store dummy accounts in order to access the GitHub API (the 3 accounts given are active)
    logins = ['ghapinamufassa3', 'ghapinamufassa1', 'ghapinamufassa2', 'ghapinamufassa4']
    passwords = ['Runyoufools1', 'Runyoufools1', 'Runyoufools1', 'Runyoufools1']

    rep = Repository.Repository('ansible', 'ansible', logins, passwords)
    rep.identifyParticipants()
    rep.activityStats(True)

    exit()

    # Exemplum gratis

    # We initialise the process by setting up the Organisation we want to fetch from GitHub
    org = Organisation.Organisation('rabbitmq', logins, passwords)

    # All repositories that are sources of the Organisation are picked up one-by-one. This procedure can take up
    # several days depending on the repository sizes. It requires some monitoring and restarting. Uncaught exceptions
    # unfortunately do happen here.
    # org.getOrgData()

    # For each repository the data gets transformed.
    # org.transformData(True)

    # The data gets collected at the organisation's level
    # org.collectParticipants(True)

    # To improve the quality of the data the mergeParticipants()-method can be used

    # org.identifyParticipants()

    # Weekly rates are calculated at the level of the organisation. The second argument (minimal departure interval)
    # needs to be chosen carefully : If the participant makes no more contribution after YYYYWW, we consider it a departure
    # org.transformWeeklyRates(True, 13)

    # The weekly rates are converted to cvs-files so that they can be furtherly utilised for data analysis.
    # org.csvFullFillWeeklyRates()

    # The development action events are converted to cvs-files so that they can be furtherly utilised for data analysis.
    # org.csvFullFillDevEvents()

    # This utility will give a high level overview of what the repository contains
    org.activityStats(True)

    exit()




