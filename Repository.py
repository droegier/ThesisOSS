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

# !/usr/bin/env python2

import itertools
import github
import os
import datetime
import lxml.etree as ET
import codecs
import time
import ssl
from isoweek import Week
import threading
import Queue
import CommitThread
import IssueThread
import UserThread
import ParticipantThread

class Repository(object):

    def __init__(self, org_name, rep_name, logins, passwords):
        # defining variables
        self.logins = logins
        self.passwords = passwords
        self.rep_name = rep_name
        self.org_name = org_name

        self.comm_page_nr = 0
        self.iss_page_nr = 0

        # threading queues
        self.commit_q = None
        self.issue_q = None
        self.user_q = None
        self.participant_q = None

        # github api references, they are built in setGitHub()
        self.g = None
        self.org = None
        self.repo = None
        self.ghi = 0

        # xml trees and roots
        self.commits_tree = None
        self.issues_tree = None
        self.users_tree = None
        self.participants_tree = None

        self.users_root = None
        self.commits_root = None
        self.issues_root = None
        self.participants_root = None

        #logger
        if not os.path.exists('data/' + org_name + '/' + rep_name):
            os.makedirs('data/' + org_name + '/' + rep_name)
        self.logger = codecs.open('data/' + org_name + '/' + rep_name + '/log',mode='a',encoding='utf-8')
        self.speak('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')

    def __del__(self):
        if self.commits_tree:
            self.commits_tree.write('data/' + self.org_name + '/' + self.rep_name + '/commits.xml')
        if self.issues_tree:
            self.issues_tree.write('data/' + self.org_name + '/' + self.rep_name + '/issues.xml')
        if self.users_tree:
            self.users_tree.write('data/' + self.org_name + '/users.xml')
        if self.participants_tree:
            self.participants_tree.write('data/' + self.org_name + '/' + self.rep_name + '/participants.xml')
        # not logger because we still want to log things after the with statement!
        if not self.logger.closed:
            self.logger.close()

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        if self.commits_tree:
            self.commits_tree.write('data/' + self.org_name + '/' + self.rep_name + '/commits.xml')
        if self.issues_tree:
            self.issues_tree.write('data/' + self.org_name + '/' + self.rep_name + '/issues.xml')
        if self.users_tree:
            self.users_tree.write('data/' + self.org_name + '/users.xml')
        if self.participants_tree:
            self.participants_tree.write('data/' + self.org_name + '/' + self.rep_name + '/participants.xml')
        if not self.logger.closed:
            self.logger.close()
        return

# UTILITY

    def setGitHub(self):
        self.g = []
        self.org = []
        self.repo = []

        for login in self.logins:
            g = github.Github(login, self.passwords[self.logins.index(login)])
            org = g.get_user(self.org_name)
            if not org:
                print 'No organisation found'
                exit()
            for repo in org.get_repos():
                if repo.name == self.rep_name:
                    rep = repo
                    break
            if not rep:
                print 'No repository found'
                exit()
            self.g.append(g)
            self.org.append(org)
            self.repo.append(rep)
        return

    def parseXml(self, filename, level): # level : 0 for saving on org-folder level, 1 for saving on rep-folder level
        if level == 0:
            if not os.path.exists('data/' + self.org_name + '/' + filename):
                tree = ET.ElementTree()
                el = ET.Element('root')
                tree._setroot(el)
                tree.write('data/' + self.org_name + '/' + filename)
            else:
                tree = ET.parse('data/' + self.org_name + '/' + filename)
                if tree.getroot().tag <> 'root': exit()
        else:
            if not os.path.exists('data/' + self.org_name + '/' + self.rep_name + '/' + filename):
                tree = ET.ElementTree()
                el = ET.Element('root')
                tree._setroot(el)
                tree.write('data/' + self.org_name + '/' + self.rep_name + '/' + filename)
            else:
                tree = ET.parse('data/' + self.org_name + '/' + self.rep_name + '/' + filename)
                if tree.getroot().tag <> 'root': exit()
        return tree

    def speak(self, str):
        if self.logger.closed:
            self.logger = codecs.open('data/' + self.org_name + '/' + self.rep_name + '/log',mode='a',encoding='utf-8')
        self.logger.write(str + '\n')
        print str

    def identifyParticipants(self):
        self.setGitHub()
        if not os.path.exists('data/' + self.org_name + '/' + self.rep_name + '/' + 'participants.xml'):
                return False
        else:
            self.participants_tree = ET.parse('data/' + self.org_name + '/' + self.rep_name + '/' + 'participants.xml')
            if self.participants_tree.getroot().tag <> 'root': exit()
        participants_root = self.participants_tree.getroot()

        locks = [threading.Lock(), threading.Lock()] # lock for print, participant
        self.part_q = Queue.Queue(maxsize=len(self.logins)+1)
        for i in range(len(self.logins)):
            t = ParticipantThread.ParticipantThread(locks, self, i)
            t.daemon = True
            t.start()
        try:
            for participant in participants_root:
                self.part_q.put(participant, block=True)
            self.part_q.join()
        finally:
            self.participants_tree.write('data/' + self.org_name + '/' + self.rep_name + '/participants.xml')
        participants_root.set('cnt',str(len(participants_root)))
        participants_root.set('identifyparticipants-status','completed')
        print "IDENTIFYPARTICIPANTS : donedone"
        self.participants_tree.write('data/' + self.org_name + '/' + self.rep_name + '/participants.xml')
        return True

    def activityStats(self, flag):
        self.participants_tree = self.parseXml('participants.xml',1)
        participants_root = self.participants_tree.getroot()
        cnt_GitHub = 0
        cnt_all = 0
        cnt_dev = 0
        cnt_dev_GitHub = 0
        cnt_GitHub_act = 0
        cnt_all_act = 0
        cnt_commits = 0
        cnt_pullrequests = 0
        cnt_issues = 0
        cnt_comments = 0
        cnt_mergers = 0
        for participant in participants_root:
            dev = 0
            for period in participant:
                if dev == 0:
                    for i in period:
                        if(i.tag=='commits' or i.tag=='mergers'):
                            dev = 1
            if dev == 1:
                cnt_dev = cnt_dev + 1
                if participant.get('profile') == 'set':
                    cnt_dev_GitHub = cnt_dev_GitHub + 1
            if participant.get('profile') == 'set':
                cnt_GitHub += 1
                cnt_all += 1
                try:
                    cnt = int(participant.get('cnt'))
                    cnt_GitHub_act += cnt
                    cnt_all_act += cnt
                except:
                    pass
            else:
                cnt_all += 1
                try:
                    cnt = int(participant.get('cnt'))
                    cnt_all_act += cnt
                except:
                    pass
            if flag == True:
                for period in participant:
                    commits = period.find('commits')
                    if commits is not None:
                        cnt_commits += int(commits.text)
                    pullrequests = period.find('pullrequests')
                    if pullrequests is not None:
                        cnt_pullrequests += int(pullrequests.text)
                    comments = period.find('comments')
                    if comments is not None:
                        cnt_comments += int(comments.text)
                    issues = period.find('issues')
                    if issues is not None:
                        cnt_issues += int(issues.text)
                    mergers = period.find('mergers')
                    if mergers is not None:
                        cnt_mergers += int(mergers.text)
        #participants_root.set('totalCnt',str(cnt_all_act))
        #self.participants_tree.write('data/' + self.org_name + '/' + 'participants.xml')
        print "----------------------\n Contributor Stats \n \n"
        print "# Total Participants : "+str(cnt_all)
        s = '%.2f'%(float(cnt_GitHub)/float(cnt_all)*100)
        r = '%.2f'%(float(cnt_GitHub_act)/float(cnt_all_act)*100)
        print "# GitHub Contributors : "+str(cnt_GitHub)+" ("+s+"%)"
        print "# Developers : "+str(cnt_dev)
        print "# GitHub Developers (post-script) : "+str(cnt_dev_GitHub)
        print "# Total development actions : "+str(cnt_all_act)
        print "# Development actions linked to GitHub account : "+str(cnt_GitHub_act)+" ("+r+"%)"

        return True

# ISSUES

    def addIssues(self,reset):
        if not self.issues_tree:
            self.issues_tree = self.parseXml('issues.xml',1)
        self.issues_root = self.issues_tree.getroot()

        if not self.g:
            self.setGitHub()

        issues_p = []
        for i in range(len(self.logins)):
            issues_p.append(self.repo[i].get_issues(state="all", direction="asc"))
        pool = itertools.cycle(issues_p)

        self.iss_page_nr = 0
        if reset:
            self.issues_root.clear()
        elif 'page' in self.issues_root.attrib:
            self.iss_page_nr = int(self.issues_root.get('page'))
            #[AMENDMENT1]
            # self.iss_page_nr = 0

        if self.issues_root.get('status') == 'done':
            #[AMENDMENT1]
            # pass
            return True
        #[AMENDMENT1]
        self.issues_root.set('status','build')

        issues = next(pool).get_page(self.iss_page_nr)

        locks = [threading.Lock(), threading.Lock()] # lock for print, issue, users

        self.issue_q = Queue.Queue(maxsize=len(self.logins)+1)

        for i in range(len(self.logins)):
            t = IssueThread.IssueThread(locks, self, i)
            t.daemon = True
            t.start()
        try:
            while len(issues) > 0:
                self.issue_q.put(issues, block=True)
                self.iss_page_nr += 1
                issues = next(pool).get_page(self.iss_page_nr)
                # COULD BE REMOVED
                #locks[1].acquire()
                #self.issues_root.set('page',str(self.iss_page_nr))
                #self.issues_tree.write('data/' + self.org_name + '/' + self.rep_name + '/issues.xml')
                #locks[1].release()
            self.issue_q.join()
            self.issues_root.set('status','done')
            self.speak("Finished " + str(self.iss_page_nr))
            return True
        except:
            self.issues_root.remove(self.issues_root[len(self.issues_root) - 1])
            raise
        finally:
            self.issues_root.set('page',str(self.iss_page_nr-3) if self.iss_page_nr-3>0 else str(0))

    def transformIssues(self,reset):
        if not self.issues_tree:
            self.issues_tree = self.parseXml('issues.xml',1)
        if not self.issues_root:
            self.issues_root = self.issues_tree.getroot()
        if not self.participants_tree:
            self.participants_tree = self.parseXml('participants.xml',1)
        if not self.participants_root:
            self.participants_root = self.participants_tree.getroot()

        if reset is True:
            self.participants_root.clear()

        if self.participants_root.get('issues-status') == 'done':
            return True

        self.participants_root.set('issues-status','build')

        try:
            for issue in self.issues_root:
                hit = self.participants_root.findall("./participant[@login='" + issue.get('creator') + "']")
                c_a = issue.get('created_at')
                if c_a is None:
                    print 'eyla'
                    continue

                date_temp = datetime.date(int(c_a[c_a.rindex('/') + 1:]),
                              int(c_a[c_a.index('/') + 1:c_a.rindex('/')]),
                              int(c_a[:c_a.index('/')]))
                date = str(date_temp.isocalendar()[0]) + str(date_temp.isocalendar()[1]).zfill(2)

                # ISSUE_CREATOR!!!
                # NEW PARTICIPANT
                if (len(hit) == 0):
                    hit = ET.SubElement(self.participants_root, 'participant')
                    hit.set('login', issue.get('creator'))
                    per = ET.SubElement(hit, 'period')
                    per.set('date', date)
                    if (issue.get('pullrequest') == 'yes'):
                        pr = ET.SubElement(per, 'pullrequests')
                        pr.text = "1"
                    else:
                        iss = ET.SubElement(per, 'issues')
                        iss.text = "1"
                    hit.set('cnt', "1")

                # PARTICIPANT HIT
                elif (len(hit) == 1):
                    hit = hit[0]
                    per = hit.findall("./period[@date='" + date + "']")
                    if (len(per) == 0):  # period not there
                        per = ET.SubElement(hit, 'period')
                        per.set('date', date)
                        if (issue.get('pullrequest') == 'yes'):
                            pr = ET.SubElement(per, 'pullrequests')
                            pr.text = "1"
                        else:  # plain issue
                            iss = ET.SubElement(per, 'issues')
                            iss.text = "1"
                        hit.set('cnt', str(int(hit.get('cnt')) + 1))
                    elif (len(per) == 1):  # period hit
                        per = per[0]
                        if (issue.get('pullrequest') == 'yes'):  # pullrequest
                            pr = per.find('pullrequests')
                            if (pr != None):
                                pr.text = str(int(pr.text) + 1)
                            else:
                                pr = ET.SubElement(per, "pullrequests")
                                pr.text = "1"
                        else:  # plain issue
                            iss = per.find('issues')
                            if (iss != None):
                                iss.text = str(int(iss.text) + 1)
                            else:
                                iss = ET.SubElement(per, "issues")
                                iss.text = "1"
                        hit.set('cnt', str(int(hit.get('cnt')) + 1))
                    else:
                        self.speak('TRANSFORMISSUES C: this should never happen: ' + issue.get(
                            'creator') + ' has period ' + date + 'stored ' + len(
                            per) + " times in participants.xml")
                else:
                    self.speak('TRANSFORMISSUES D : this should never happen: ' + issue.get('creator') + ' is stored ' + len(
                        hit) + " times in participants.xml")

                for comment in issue:
                    hit = self.participants_root.findall("./participant[@login='" + comment.get('creator') + "']")
                    c_a = comment.get('created_at')
                    date_temp = datetime.date(int(c_a[c_a.rindex('/') + 1:]),
                              int(c_a[c_a.index('/') + 1:c_a.rindex('/')]),
                              int(c_a[:c_a.index('/')]))
                    date = str(date_temp.isocalendar()[0]) + str(date_temp.isocalendar()[1]).zfill(2)

                    # COMMENT_CREATOR
                    # NEW PARTICIPANT
                    if (len(hit) == 0):
                        hit = ET.SubElement(self.participants_root, 'participant')
                        hit.set('login', comment.get('creator'))
                        per = ET.SubElement(hit, 'period')
                        per.set('date', date)
                        com = ET.SubElement(per, 'comments')
                        com.text = "1"
                        hit.set('cnt', "1")

                    # PARTICIPANT HIT
                    elif (len(hit) == 1):
                        hit = hit[0]
                        per = hit.findall("./period[@date='" + date + "']")
                        if (len(per) == 0):  # period not there
                            per = ET.SubElement(hit, 'period')
                            per.set('date', date)
                            com = ET.SubElement(per, 'comments')
                            com.text = "1"
                            hit.set('cnt', str(int(hit.get('cnt')) + 1))
                        elif (len(per) == 1):  # period hit
                            per = per[0]
                            com = per.find('comments')
                            if (com != None):
                                com.text = str(int(com.text) + 1)
                            else:
                                com = ET.SubElement(per, "comments")
                                com.text = "1"
                            hit.set('cnt', str(int(hit.get('cnt')) + 1))
                        else:
                            self.speak('TRANSFORMISSUES B: this should never happen: ' + comment.get(
                                'creator') + ' has period ' + date + 'stored ' + len(
                                per) + " times in participants.xml")
                    else:
                        self.speak('TRANSFORMISSUES A: this should never happen: ' + comment.get('creator') + ' is stored ' + len(
                            hit) + " times in participants.xml")
        except:
            raise
        self.participants_root.set('issues-status','done')
        self.speak("TRANSFORMISSUES : donedone")
        self.participants_tree.write('data/' + self.org_name + '/' + self.rep_name + '/participants.xml')
        return True

# COMMITS

    def populateUserLinks(self, reset):
        if not self.users_root:
            if not self.users_tree:
                self.users_tree = self.parseXml('users.xml',0)
            self.users_root = self.users_tree.getroot()

        if reset == True:
            #self.users_root.clear()
            pass
        elif self.users_root.get('populated-rep-'+self.rep_name) == 'done':
            return

        locks = [threading.Lock(), threading.Lock()] # lock for print, user
        self.user_q = Queue.Queue(maxsize=len(self.logins)+1)
        for i in range(len(self.logins)):
            t = UserThread.UserThread(locks, self, i)
            t.daemon = True
            t.start()

        if self.users_root.get('populated-org-'+self.org_name) <> 'done':
            mems_p = []
            for i in range(len(self.logins)):
                try:
                    mems_p.append(self.g[i].get_organization(self.org_name).get_members())
                except:
                    return
            pool = itertools.cycle(mems_p)
            mems_page_nr = 0
            mems = next(pool).get_page(mems_page_nr)
            while len(mems) > 0:
                self.user_q.put(mems, block=True)
                mems_page_nr += 1
                mems = next(pool).get_page(mems_page_nr)
                locks[1].acquire()
                try:
                    self.users_tree.write('data/' + self.org_name + '/' + 'users.xml')
                finally:
                    locks[1].release()
            # wait for queue to run out
            self.user_q.join()
            self.users_root.set('populated-org-'+self.org_name,'done')

        contr_p = []
        for i in range(len(self.logins)):
            try:
                contr_p.append(self.repo[i].get_contributors())
            except:
                return
        pool = itertools.cycle(contr_p)
        contr_page_nr = 0
        try:
            contr = next(pool).get_page(contr_page_nr)
        except:
            return
        while len(contr) > 0:
            self.user_q.put(contr, block=True)
            contr_page_nr += 1
            contr = next(pool).get_page(contr_page_nr)
            locks[1].acquire()
            try:
                self.users_tree.write('data/' + self.org_name + '/' + 'users.xml')
            finally:
                locks[1].release()
        # wait for queue to run out
        self.user_q.join()
        self.users_root.set('populated-rep-'+self.rep_name, 'done')

        self.users_tree.write('data/' + self.org_name + '/users.xml')
        print 'done populating'

    def addCommits(self,reset):

        if not self.commits_tree:
            self.commits_tree = self.parseXml('commits.xml',1)
        self.commits_root = self.commits_tree.getroot()

        if not self.g:
            self.setGitHub()

        commits_p = []
        for i in range(len(self.logins)):
            commits_p.append(self.repo[i].get_commits())
        pool = itertools.cycle(commits_p)

        self.comm_page_nr = 0
        if reset:
            self.commits_root.clear()

        elif self.commits_root.get('page') is not None:
            self.comm_page_nr = int(self.commits_root.get('page'))
            #[AMENDMENT1]
            # self.comm_page_nr = 0

        if self.commits_root.get('status') == 'done':
            #[AMENDMENT1]
            #pass
            return True

        self.commits_root.set('status','build')

        self.populateUserLinks(reset)

        commits = next(pool).get_page(self.comm_page_nr)


        locks = [threading.Lock(), threading.Lock(), threading.Lock()] # lock for print, commit, users
        self.commit_q = Queue.Queue(maxsize=len(self.logins)+1)
        for i in range(len(self.logins)):
            t = CommitThread.CommitThread(locks, self, i)
            t.daemon = True
            t.start()

        try:
            while len(commits) > 0:
                self.commit_q.put(commits, block=True)
                self.comm_page_nr += 1
                commits = next(pool).get_page(self.comm_page_nr)
            # wait for queue to run out
            self.commit_q.join()

            self.commits_root.set('status','done')
            self.speak( "Commits Finished " + str(self.comm_page_nr))
            return True
        except:
            self.commits_root.remove(self.commits_root[len(self.commits_root) - 1])
            raise
        finally:
            self.commits_root.set('page',str(self.comm_page_nr-3) if self.comm_page_nr-3>0 else str(0))

    def transformCommits(self, reset):
        if not self.commits_tree:
            self.commits_tree = self.parseXml('commits.xml',1)
        if not self.commits_root:
            self.commits_root = self.commits_tree.getroot()
        if not self.participants_tree:
            self.participants_tree = self.parseXml('participants.xml',1)
        if not self.participants_root:
            self.participants_root = self.participants_tree.getroot()
        if reset:
            self.participants_root.clear()

        if self.participants_root.get('commits-status') == 'done':
            return True

        self.participants_root.set('commits-status','build')
        try:
            for commit in self.commits_root:
                hit = self.participants_root.findall("./participant[@login='" + commit.get('creator') + "']")
                c_a = commit.get('created_at')

                # insert period as week of datetime
                date_temp = datetime.date(int(c_a[c_a.rindex('/') + 1:]),
                              int(c_a[c_a.index('/') + 1:c_a.rindex('/')]),
                              int(c_a[:c_a.index('/')]))
                date = str(date_temp.isocalendar()[0]) + str(date_temp.isocalendar()[1]).zfill(2)

                # ISSUE_CREATOR!!!
                # NEW PARTICIPANT
                if (len(hit) == 0):
                    hit = ET.SubElement(self.participants_root, 'participant')
                    hit.set('login', commit.get('creator'))
                    per = ET.SubElement(hit, 'period')
                    per.set('date', date)
                    if (commit.get('merge') == 'yes'):
                        pr = ET.SubElement(per, 'mergers')
                        pr.text = "1"
                    else:
                        iss = ET.SubElement(per, 'commits')
                        iss.text = "1"
                        add = ET.SubElement(per, 'additions')
                        add.text = str(commit.get('additions'))
                        dele = ET.SubElement(per, 'deletions')
                        dele.text = str(commit.get('deletions'))
                    hit.set('cnt', "1")

                # PARTICIPANT HIT
                elif (len(hit) == 1):
                    hit = hit[0]

                    per = hit.findall("./period[@date='" + date + "']")
                    if (len(per) == 0):  # period not there
                        per = ET.SubElement(hit, 'period')
                        per.set('date', date)
                        if (commit.get('merge') == 'yes'):
                            pr = ET.SubElement(per, 'mergers')
                            pr.text = "1"
                        else:  # plain issue
                            iss = ET.SubElement(per, 'commits')
                            iss.text = "1"
                            add = ET.SubElement(per, 'additions')
                            add.text = str(commit.get('additions'))
                            dele = ET.SubElement(per, 'deletions')
                            dele.text = str(commit.get('deletions'))
                        hit.set('cnt', str(int(hit.get('cnt')) + 1))
                    elif (len(per) == 1):  # period hit
                        per = per[0]
                        if (commit.get('merge') == 'yes'):  # pullrequest
                            pr = per.find('mergers')
                            if (pr != None):
                                pr.text = str(int(pr.text) + 1)
                            else:
                                pr = ET.SubElement(per, "mergers")
                                pr.text = "1"
                        else:  # plain issue
                            iss = per.find('commits')
                            if (iss != None):
                                iss.text = str(int(iss.text) + 1)
                                add = per.find('additions')
                                add.text = str(int(add.text)+int(commit.get('additions')))
                                dele = per.find('deletions')
                                dele.text = str(int(dele.text)+int(commit.get('deletions')))
                            else:
                                iss = ET.SubElement(per, "commits")
                                iss.text = "1"
                                add = ET.SubElement(per, 'additions')
                                add.text = str(commit.get('additions'))
                                dele = ET.SubElement(per, 'deletions')
                                dele.text = str(commit.get('deletions'))
                        hit.set('cnt', str(int(hit.get('cnt')) + 1))
                    else:
                        self.speak('TRANSFORMCOMMITS C : this should never happen: ' + commit.get(
                            'creator') + ' has period ' + date + 'stored ' + len(
                            per) + " times in participants.xml")
                else:
                    self.speak('TRANSFORMCOMMITS D : this should never happen: ' + commit.get('creator') + ' is stored ' + len(
                        hit) + " times in participants.xml")

                for comment in commit:
                    hit = self.participants_root.findall("./participant[@login='" + comment.get('creator') + "']")
                    c_a = comment.get('created_at')
                    date_temp = datetime.date(int(c_a[c_a.rindex('/') + 1:]),
                              int(c_a[c_a.index('/') + 1:c_a.rindex('/')]),
                              int(c_a[:c_a.index('/')]))
                    date = str(date_temp.isocalendar()[0]) + str(date_temp.isocalendar()[1]).zfill(2)

                    # COMMENT_CREATOR
                    # NEW PARTICIPANT
                    if (len(hit) == 0):
                        hit = ET.SubElement(self.participants_root, 'participant')
                        hit.set('login', comment.get('creator'))
                        per = ET.SubElement(hit, 'period')
                        per.set('date', date)
                        com = ET.SubElement(per, 'comments')
                        com.text = "1"
                        hit.set('cnt', "1")

                    # PARTICIPANT HIT
                    elif (len(hit) == 1):
                        hit = hit[0]
                        per = hit.findall("./period[@date='" + date + "']")
                        if (len(per) == 0):  # period not there
                            per = ET.SubElement(hit, 'period')
                            per.set('date', date)
                            com = ET.SubElement(per, 'comments')
                            com.text = "1"
                            hit.set('cnt', str(int(hit.get('cnt')) + 1))
                        elif (len(per) == 1):  # period hit
                            per = per[0]
                            com = per.find('comments')
                            if (com != None):
                                com.text = str(int(com.text) + 1)
                            else:
                                com = ET.SubElement(per, "comments")
                                com.text = "1"
                            hit.set('cnt', str(int(hit.get('cnt')) + 1))
                        else:
                            self.speak('TRANSFORMCOMMITS B : this should never happen: ' + comment.get(
                                'creator') + ' has period ' + date + 'stored ' + len(
                                per) + " times in participants.xml")
                    else:
                        self.speak( 'TRANSFORMCOMMITS A : this should never happen: ' + comment.get('creator') + ' is stored ' + len(
                            hit) + " times in participants.xml")

        # add a try and finally loop to write the data collection to participants.xml
        except:
            raise
        self.participants_root.set('commits-status','done')
        self.speak("TRANSFORMCOMMITS : donedone")
        self.participants_tree.write('data/' + self.org_name + '/' + self.rep_name + '/participants.xml')
        return True

# STATIC FUNCTIONS

def encodeXml(str):
    str = str.replace("'", "&apos;")
    str = str.replace('"', "&quot;")
    return str

def decodeXml(str):
    str = str.replace("&apos;", "'")
    str = str.replace("&quot;", "\"")
    return str

