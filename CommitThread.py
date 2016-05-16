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
CommitThread picks up commits from a repository and stores them in the 'commits.xml' file. This is a bit more
complicated then the other thread classes, as some heuristics are involved to link the right GitHub account
based on the git data.
"""

import threading
import xml.etree.ElementTree as ET
import codecs
import Repository
import time
import ssl
import github

class CommitThread (threading.Thread):

    def __init__(self, locks, repository, gh_iterator):
        threading.Thread.__init__(self)
        self.lock_p = locks[0]
        self.lock_c = locks[1]
        self.lock_u = locks[2]
        self.R = repository
        self.ghi = gh_iterator

    def run(self):
        try:
            while True:
                commits = self.R.commit_q.get()
                for commit in commits:
                    self.lock_c.acquire()
                    try:
                        chk = self.R.commits_root.findall("./commit[@id='" + commit.sha + "']")
                    finally:
                        self.lock_c.release()
                    #[AMENDMENT1]
                    if (len(chk) == 0) and (commit.commit.committer.date.isocalendar()[0]*100+commit.commit.committer.date.isocalendar()[1] < 201618):
                    #if (len(chk) == 0) and commit.commit.committer.date.isocalendar()[0] < 2016:
                        flag = False
                        while not flag:
                            try:
                                flag = self.handleCommit(commit)
                            except ssl.SSLError as error:
                                print ' catched SSL : ' + error.message
                                time.sleep(5)
                            except github.GithubException as error:
                                print error.message
                                print 'sleeping'
                                for g in self.R.g:
                                    if g.get_rate_limit().rate.remaining == 0:
                                        print 'sleeping'
                                        time.sleep(g.rate_limiting_resettime - int(time.time()) + 10)
                            except Exception as error:
                                if error.message == '_ssl.c:574: The handshake operation timed out':
                                    print error.message
                                    time.sleep(5)
                                else:
                                    raise
                        ################################
                    self.lock_p.acquire()
                    try:
                        print "commit" + str(commit.commit.committer.date.day) + '.' + str(
                            commit.commit.committer.date.month) + '.' + str(
                            commit.commit.committer.date.year)
                    finally:
                        self.lock_p.release()
                self.lock_p.acquire()
                try:
                    print self.R.g[self.ghi].get_user().login + '-cycle complete'
                finally:
                    self.lock_p.release()
                self.R.commit_q.task_done()
        finally:
            self.lock_c.acquire() #a = '123' if b else '456'
            try:
                self.R.commits_root.set('page',str(self.R.comm_page_nr-3) if self.R.comm_page_nr-3>0 else str(0))
                self.R.commits_tree.write('data/' + self.R.org_name + '/' + self.R.rep_name + '/commits.xml')
            finally:
                self.lock_c.release()
            self.lock_u.acquire()
            try:
                self.R.users_tree.write('data/' + self.R.org_name + '/users.xml')
            finally:
                self.lock_u.release()

    def handleCommit(self,commit):
        el = 0  # IF ITS A BRANCH MERGE, WE DONT CONSIDER IT
        ####################################################################
        if commit.commit.message.find("Merge branch '") == 0:
            # we ignore this case, it represents simple merging of commits for organisation, without actually verifying the code, which is captured in the next elif
            return True

        # WE TRY AND MAKE SURE THE CORRECT GITHUB ACCOUNTS ARE SET FOR THE COMMITTER AND AUTHOR
        ####################################################################
        logina = ''
        loginc = ''
        if commit.committer is not None and commit.author is not None:
            # both are set ok, good to go
            logina = commit.author.login
            loginc = commit.committer.login
            pass
        elif commit.committer is not None:  # this means the githubauthor is not set
            loginc = commit.committer.login
            if commit.commit.author.name == commit.commit.committer.name \
                    or commit.commit.author.name == commit.committer.login \
                    or commit.commit.author.name == commit.committer.name:
                # if based on the git data, we can detect that the author and committer are the same person, we can pull that link on the github level
                logina = commit.committer.login
                self.writeUserLink([commit.commit.author.name], logina)
            else:
                logina = self.searchUserLink([commit.commit.author.name], True)
                if logina == '':
                    # touched case : look for an according pull request

                    ret = self.R.g[self.ghi].search_issues(commit.sha)
                    for i in ret:
                        if i.pull_request and i.repository.full_name == self.R.org_name + '/' + self.R.rep_name:
                            s = self.R.repo[self.ghi].get_pull(i.number).head.label
                            s = s[:s.find(':')]
                            if s <> self.R.org_name and s <> loginc:
                                logina = s
                                self.writeUserLink([commit.commit.author.name], logina)
                                break
                if logina == '':
                    logina = commit.commit.author.email + '//' + commit.commit.author.name
                    self.speak(
                        'ADDCOMMITS: Found committer, but not author, so for that one we used the e-mailaddress ' + logina + ' // ' + commit.sha)
        elif commit.author is not None:  # same as above but githubcommitter
            logina = commit.author.login
            if commit.commit.committer.name == commit.commit.author.name \
                    or commit.commit.committer.name == commit.author.login \
                    or commit.commit.committer.name == commit.author.name:
                # if based on the git data, we can detect that the author and committer are the same person, we can pull that link on the github level
                loginc = commit.author.login
                self.writeUserLink([commit.commit.committer.name], loginc)
            else:
                loginc = self.searchUserLink([commit.commit.committer.name], True)
                if loginc == '':
                    # touched case : look for an according pull request
                    ret = self.R.g[self.ghi].search_issues(commit.sha)
                    for i in ret:
                        if i.pull_request and i.repository.full_name == self.R.org_name + '/' + self.R.rep_name:
                            s = self.R.repo[self.ghi].get_pull(i.number).head.label
                            s = s[:s.find(':')]
                            if s <> self.R.org_name and s <> logina:
                                loginc = s
                                self.writeUserLink([commit.commit.committer.name], loginc)
                                break
                if loginc == '':
                    loginc = commit.commit.committer.email + '//' + commit.commit.committer.name
                    self.speak(
                        'ADDCOMMITS: Found author, but not committer, so for that one we used the e-mailaddress ' + loginc + ' // ' + commit.sha)
        else:  # both are not set:
            # CASE 1 : same person according to git
            if commit.commit.committer.name == commit.commit.author.name \
                    or commit.commit.committer.email == commit.commit.author.email:
                loginc = self.searchUserLink([commit.commit.committer.name], True)
                if loginc == '':
                    # DO THE PULLREQUEST TRY
                    ret = self.R.g[self.ghi].search_issues(commit.sha)
                    for i in ret:
                        if i.pull_request and i.repository.full_name == self.R.org_name + '/' + self.R.rep_name:
                            s = self.R.repo[self.ghi].get_pull(i.number).head.label
                            s = s[:s.find(':')]
                            if s <> self.R.org_name:
                                loginc = s
                                self.writeUserLink([commit.commit.committer.name, commit.commit.author.name], loginc)
                                break
                if loginc == '':
                    loginc = commit.commit.committer.email + '//' + commit.commit.author.email + '//' + commit.commit.committer.name + '//' + commit.commit.author.name
                    self.speak(
                        'ADDCOMMITS: According to git author and committer are the same, but no resolve, so for that one we used the two e-mailaddresses ' + loginc + ' // ' + commit.sha)
                logina = loginc
            # CASE 2 : different person according to git
            else:
                # RESOLVE LOGINC
                loginc = self.searchUserLink([commit.commit.committer.name], True)
                logina = self.searchUserLink([commit.commit.author.name], True)
                if loginc == '':
                    # DO THE PULLREQUEST TRY
                    ret = self.R.g[self.ghi].search_issues(commit.sha)
                    for i in ret:
                        if i.pull_request and i.repository.full_name == self.R.org_name + '/' + self.R.rep_name:
                            s = self.R.repo[self.ghi].get_pull(i.number).head.label
                            s = s[:s.find(':')]
                            if s <> self.R.org_name and s <> logina:
                                loginc = s
                                self.writeUserLink([commit.commit.committer.name], loginc)
                                break
                if loginc == '':
                    loginc = commit.commit.committer.email + '//' + commit.commit.committer.name
                    self.speak(
                        'ADDCOMMITS: According to git author and committer are not the same, no resolve for committer so we use email ' + loginc + ' // ' + commit.sha)
                if logina == '':
                    # DO THE PULLREQUEST TRY
                    ret = self.R.g[self.ghi].search_issues(commit.sha)
                    for i in ret:
                        if i.pull_request and i.repository.full_name == self.R.org_name + '/' + self.R.rep_name:
                            s = self.R.repo[self.ghi].get_pull(i.number).head.label
                            s = s[:s.find(':')]
                            if s <> self.R.org_name and s <> loginc:
                                logina = s
                                self.writeUserLink([commit.commit.author.name], loginc)
                                break
                if logina == '':
                    logina = commit.commit.author.email + '//' + commit.commit.author.name
                    self.speak(
                        'ADDCOMMITS: According to git author and committer are not the same, no resolve for author so we use email ' + logina + ' // ' + commit.sha)
        if logina == '' or loginc == '':
            self.speak('ADDCOMMITS: this should not happen!!' + commit.sha)
        ####################################################################

        # NOW WE SIMPLY WRITE THE COMMIT(S)
        ####################################################################
        if commit.commit.message.find('Merge pull request') == 0:
            if loginc <> logina:
                self.speak('ADDCOMMITS: this is strange double check it!!' + commit.sha)
            i = commit.commit.message.find('from')
            j = commit.commit.message.find('/')
            # should we check for both?
            if commit.commit.message[i + 5:j] == logina \
                    or commit.commit.message[i + 5:j] == loginc \
                    or commit.commit.message[i + 5:j] == self.R.org_name:
                # the user merges his own commit, this is not representative of any action, example : https://github.com/ansible/ansible/commit/f99b8345831b8327f973e1a92fe6a7341cce9d35
                # so we do nothing
                pass
            else:
                el = self.writeCommit(loginc, 'yes', 0, 0, commit.commit.committer.date, commit.sha)
        elif loginc <> logina:
            el = self.writeCommit(logina, 'no', commit.stats.additions, commit.stats.deletions,
                                  commit.commit.author.date, commit.sha)
            el = self.writeCommit(loginc, 'yes', 0, 0, commit.commit.committer.date, commit.sha)
        elif loginc == logina:
            el = self.writeCommit(logina, 'no', commit.stats.additions, commit.stats.deletions,
                                  commit.commit.author.date, commit.sha)
        else:
            self.speak('ADDCOMMITS: This should not happen (2)!')
        ####################################################################

        # WRITE THE COMMENTS!
        ####################################################################
        if el <> 0:
            # CHECK IF THERE ARE COMMENTS IN THE COMMIT BEFORE CALLING THE API
            comments = commit.get_comments()
            for comment in comments:
                self.lock_c.acquire()
                try:
                    el_c = ET.SubElement(el, 'comment')
                    el_c.set('creator', comment.user.login)
                    el_c.set('created_at', str(comment.created_at.day) +
                          '/' + str(comment.created_at.month) + '/' +
                             str(comment.created_at.year))
                finally:
                    self.lock_c.release()
                ####################################################################
        return True

    def writeUserLink(self, links, login):
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

    def searchUserLink(self, links, api):
        # make sure links is an array of strings!!! even if only one
        assert not isinstance(links, basestring)

        login = ''
        if self.R.users_root is None:
            if self.R.users_tree is None:
                self.R.users_tree = self.R.parseXml('users.xml',0)
            self.R.users_root = self.R.users_tree.getroot()
        for link in links:
            self.lock_u.acquire()
            try:
                login = self.R.users_root.findtext("./user[@link='"+link+"']",'')
            finally:
                self.lock_u.release()
            if login <> '':
                break
        # now we connect to github to use the search field based on the name

        if login == '' and api:
            count = 0
            for link in links:
                if len(link) > 4:       # TO+DFO require minimal lenght of the link!!!
                    ret = self.R.g[self.ghi].search_users((link + ' repo:' + self.R.org_name + '/' + self.R.rep_name).encode('utf8'))
                    self.speak('SearchUserLink : We are looking for ' + link + ' in GitHub... Now we go through the forks.')
                    if ret.totalCount < 20: #test
                        for i in ret:
                            for p in i.get_repos():
                                if p.name == self.R.rep_name and p.fork:
                                    login = login + '//' + i.login
                                    count = count + 1
                    if count <> 0: break
            if count == 0:
                self.speak('SearchUserLink: no result ... back to main function.')
            elif count == 1:
                #remove the double slash
                login = login[2:]
                self.speak('SearchUserLink: we found a single hit : ' + login)
                self.writeUserLink(links, login)
            elif count > 1:
                self.speak('SearchUserLink: Several possibilities were found  : ' + login + '. We gave that name to the commit, but didnt write it in UserLink')
                login = ''
        return login

    def writeCommit(self, login, merge, additions, deletions, date, sha):
        self.lock_c.acquire()
        try:
            el = ET.SubElement(self.R.commits_root,'commit')
            el.set('creator',login)
            el.set('merge',merge)
            el.set('created_at', str(date.day) + '/' + str(date.month) + '/' + str(date.year))
            el.set('id',sha)
            if merge == 'no':
                el.set('additions',str(additions))
                el.set('deletions',str(deletions))
        finally:
            self.lock_c.release()
        return el

    def speak(self, str):
        self.lock_p.acquire()
        try:
            if self.R.logger.closed:
                self.R.logger = codecs.open('data/' + self.R.org_name + '/' + self.R.rep_name + '/log',mode='a',encoding='utf-8')
            self.R.logger.write(str + '\n')
            print str
        finally:
            self.lock_p.release()
