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
UserThread is the class that implements a worker thread object which picks up GitHub user accounts
and writes their account data in the 'users.xml' file in the Organisation's folder. This will help later to link
git to GitHub accounts. This class is called by the Repository class to go through the repository contributors list
and the organisation's members list.
"""

import threading
import xml.etree.ElementTree as ET
import codecs
import Repository

class UserThread (threading.Thread):

    def __init__(self, locks, repository, gh_iterator):
        threading.Thread.__init__(self)
        self.lock_p = locks[0]
        self.lock_u = locks[1]
        self.R = repository
        self.ghi = gh_iterator

    def run(self):
        while True:
            users = self.R.user_q.get()
            for user in users:
                if user.name is not None:
                    self.writeUserLink([user.name], user.login)
            self.lock_p.acquire()
            try:
                print self.R.g[self.ghi].get_user().login + '-cycle complete'
            finally:
                self.lock_p.release()
            self.R.user_q.task_done()

    def writeUserLink(self, links, login):
        # make sure links is an array of strings!!! even if only one
        assert not isinstance(links, basestring)

        if self.R.users_root is None:
            if self.R.users_tree is None:
                self.R.users_tree = self.R.parseXml('users.xml',0)
            self.R.users_root = self.R.users_tree.getroot()
        if login <> '':
            for link in links:
                self.lock_u.acquire()
                try:
                    hit = self.R.users_root.findtext("./user[@link='" + Repository.encodeXml(link) + "']",'')
                finally:
                    self.lock_u.release()
                if hit == '':
                    self.speak("WriteUserLink : Adding a UserLink : " + login + '// ' + link)
                    self.lock_u.acquire()
                    try:
                        el = ET.SubElement(self.R.users_root,'user')
                        el.set('link',link)
                        el.text = login
                    finally:
                        self.lock_u.release()
                elif login <> hit:
                    self.speak("USERLINK ERROR : CONFLICT DETECTED IN USERS " + login + '// ' + link)
        else:
            self.speak("USERLINK ERROR : trying to write an empty string : " + login)

    def speak(self, str):
        self.lock_p.acquire()
        try:
            if self.R.logger.closed:
                self.R.logger = codecs.open('data/' + self.R.org_name + '/' + self.R.rep_name + '/log',mode='a',encoding='utf-8')
            self.R.logger.write(str + '\n')
            print str
        finally:
            self.lock_p.release()
