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
This class is a working thread used by the Organisation class to get information from a GitHub user account
and store them in the 'participants.xml' file.
"""

import threading
import codecs

class ParticipantThread(threading.Thread):

    def __init__(self, locks, organisation, gh_iterator):
        threading.Thread.__init__(self)
        self.lock_p = locks[0]
        self.lock_par = locks[1]
        self.O = organisation
        self.ghi = gh_iterator

    def run(self):
        try:
            while True:
                participant = self.O.part_q.get()
                self.get(participant)
                self.O.part_q.task_done()
        finally:
            self.O.participants_tree.write('data/' + self.O.org_name + '/' + self.O.rep_name + '/participants.xml')

    def get(self, participant):
        if 'profile' not in participant.attrib:
            go = 1
        else:
            go = 1
        if go:
            try:
                self.lock_par.acquire()
                try:
                    login = participant.get('login')
                finally:
                    self.lock_par.release()
                user = self.O.g[self.ghi].get_user(login.encode('utf8'))
                organ = ''
                for org in user.get_orgs():
                    organ = organ + '//' + org.login
                self.lock_par.acquire()
                try:
                    participant.set('org', organ)
                    if user.email:
                        participant.set('email', user.email)
                    if user.blog:
                        participant.set('blog', user.blog)
                    if user.company:
                        participant.set('company', user.company)
                    participant.set('created_at', str(user.created_at.date()))
                    if user.followers is not None:
                        participant.set('followers', str(user.followers))
                    if user.following is not None:
                        participant.set('following', str(user.following))
                    if user.public_repos is not None:
                        participant.set('public_repos', str(user.public_repos))
                    participant.set('profile', 'set')
                finally:
                    self.lock_par.release()
            except:
                self.lock_par.acquire()
                try:
                    participant.set('profile', 'miss')
                finally:
                    self.lock_par.release()
            self.lock_p.acquire()
            try:
                print login
            finally:
                self.lock_p.release()

    def speak(self, str):
        self.lock_p.acquire()
        try:
            print str
        finally:
            self.lock_p.release()
