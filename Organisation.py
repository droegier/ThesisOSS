# -*- coding: utf-8 -*-

# ########################## Copyrights and license ############################
#                                                                              #
# Copyright 2016 David Roegiers <david.roegiers@gmail.com>                     #
#                                                                              #
# This file is part of the author's master thesis on OSS research              #
# https://github.com/droegier/ThesisOSS                                        #
#                                                                              #
# This script is free software: you can redistribute it and/or modify it under #
# the terms of the GNU Lesser General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)    #
# any later version.                                                           #
#                                                                              #
# The following code is based on Python 2.7.10                                 #
# using the external PyGithub library v 1.26.0                                 #
# http://pygithub.github.io/PyGithub/v1/introduction.html                      #
#                                                                              #
# ##############################################################################

"""
The 'Organisation' class serves to gather all repositories that are sourced under a GitHub organisation.
All development information is stored in xml files in the data folder.
Each organisation gets its own folder with a subfolder for each repository.
"""

import Repository
import xlsxwriter
import github
import os
import datetime
import xml.etree.ElementTree as ET
import codecs
import time
import ssl
from isoweek import Week
import ParticipantThread
import threading
import Queue
import csv

class Organisation(object):

    def __init__(self, org_name, logins, passwords): # auth represents an int that chooses which login password combination to use
        self.org_name = org_name
        self.logins = logins
        self.passwords = passwords
        self.reps = None
        self.reps_status = None
        self.reps_contr_cnt = None
        self.participants_tree = None
        self.acq_week = None
        self.acqd_firm = None
        self.acqg_firm = None

    def __del__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass

# REPOSITORY COLLECTION

    def getOrgData(self):
        if self.reps is None:
            self.listReps()

        for rep in self.reps:
            print 'GETTING THE REPOSITORY : ' + rep + ' from org : '+self.org_name
            ret = self.getRepData(rep)
            if ret == True:
                print 'GATHERED THE REPOSITORY : ' + rep + ' from org : '+self.org_name

    def listReps(self):
        self.reps = []
        self.reps_status = []
        self.reps_contr_cnt = []
        self.g = github.Github(self.logins[0], self.passwords[0])
        self.org = self.g.get_user(self.org_name)
        if not self.org:
            print 'No organisation found'
            exit()
        for repo in self.org.get_repos():
            if repo.fork == False and repo.owner.login == self.org_name and repo.organization.login == self.org_name and repo.mirror_url is None:
                self.reps.append(repo.name)
                self.reps_status.append('idle')
                self.reps_contr_cnt.append(repo.get_contributors().totalCount)
        print self.reps

    def getRepData(self, rep_name):
        ret = [False, False, False, False, False, False]
        while not ret[0]:
            try :
                RC = Repository.Repository(self.org_name, rep_name, self.logins, self.passwords)
                with RC:
                    if not ret[1]:
                        ret[1] = RC.addCommits(False)
                    if not ret[2]:
                        ret[2] = RC.addIssues(False)
                    ret[0] = True
            except Exception as error:
                print error.message
                time.sleep(5)
                raise
        return True

# DATA TRANSFORMATION

    # This method transforms the data from event- to user-based for each repository within their folder
    def transformData(self,reset):
        if self.reps is None:
            self.listReps()

        for rep in self.reps:
            print 'TRANSFORMING THE REPOSITORY : ' + rep + ' from org : '+self.org_name
            RC = Repository.Repository(self.org_name, rep, self.logins, self.passwords)
            ret = RC.transformIssues(reset)
            ret = RC.transformCommits(False)
            if ret == True:
                print 'TRANSFORMED THE REPOSITORY : ' + rep + ' from org : '+self.org_name

    # This method will pick up all contributors of the repositories and collect them in an organisation-level
    # 'participants.xml'-file
    def collectParticipants(self,reset):
        if not os.path.exists('data/' + self.org_name + '/' + 'participants.xml'):
                op_tree = ET.ElementTree()
                el = ET.Element('root')
                op_tree._setroot(el)
                op_tree.write('data/' + self.org_name + '/' + 'participants.xml')
        else:
            op_tree = ET.parse('data/' + self.org_name + '/' + 'participants.xml')
            if op_tree.getroot().tag <> 'root': exit()
        op_root = op_tree.getroot()

        if op_root.get('status') == 'done' and reset == False:
            return True
        if reset == True:
            if op_root.get('acq_week') is not None:
                acq_week = op_root.get('acq_week')
            if op_root.get('acqg_firm') is not None:
                acqg_firm = op_root.get('acqg_firm')
            if op_root.get('acqd_firm') is not None:
                acqd_firm = op_root.get('acqd_firm')
            op_root.clear()
            if 'acq_week' in locals():
                op_root.set('acq_week',acq_week)
            if 'acqg_firm' in locals():
                op_root.set('acqg_firm',acqg_firm)
            if 'acqd_firm' in locals():
                op_root.set('acqd_firm',acqd_firm)

        subdirs = [x[0] for x in os.walk('data/' + self.org_name)]
        for subdir in subdirs:
            if subdir <> 'data/' + self.org_name:
                rep = subdir[subdir.rindex('/')+1:]
                if os.path.exists('data/' + self.org_name + '/' + rep + '/' + 'participants.xml'):
                    rp_tree = ET.parse('data/' + self.org_name + '/' + rep + '/' + 'participants.xml')
                    rp_root = rp_tree.getroot()
                    if rp_root.tag <> 'root': continue
                    rp_root = rp_tree.getroot()
                    for participant in rp_root:
                        ret = op_root.findall("./participant[@login='"+participant.get('login')+"']")
                        if len(ret) == 1:
                            ret = ret[0]
                            for rper in participant:
                                oper = ret.findall("./period[@date='"+rper.get('date')+"']")
                                if len(oper) == 1:
                                    oper = oper[0]
                                    for rtyp in rper:
                                        otyp = oper.findall("./"+rtyp.tag)
                                        if len(otyp) == 1:
                                            otyp = otyp[0]
                                            otyp.text = str(int(rtyp.text) + int(otyp.text))
                                        elif len(otyp) == 0:
                                            oper.append(rtyp)
                                        else:
                                            print "ERR : double element types in single period "
                                elif len(oper) == 0:
                                    ret.append(rper)
                                elif len(oper) > 1:
                                    print "ERR : multiple period hit in single participant"
                                else:
                                    print "ERR : strange..."
                            ret.set('cnt', str(int(ret.get('cnt')) + int(participant.get('cnt'))))
                        elif len(ret) == 0:
                            op_root.append(participant)
                        else:
                            print 'ERR : this is STRANGE and shouldnt happen'
                        print participant.get('login')
                print 'finished repository : ' + rep
                op_tree.write('data/' + self.org_name + '/' + 'participants.xml')
                op_root.set(rep,'done')
        op_root.set('status','done')
        op_tree.write('data/' + self.org_name + '/' + 'participants.xml')

    # This functions allows to merge two participants in the participant.xml file together.
    def mergeParticipants(self, one, two):
        # two will disappear and be added to one
        if not os.path.exists('data/' + self.org_name + '/' + 'participants.xml'):
                return False
        else:
            self.participants_tree = ET.parse('data/' + self.org_name + '/' + 'participants.xml')
            if self.participants_tree.getroot().tag <> 'root': exit()
        participants_root = self.participants_tree.getroot()

        r1 = participants_root.findall("./participant[@login='"+one+"']")
        r2 = participants_root.findall("./participant[@login='"+two+"']")
        if len(r1) == 1 & len(r2) == 1:
            r2 = r2[0]
            r1 = r1[0]
            for per2 in r2:
                per1 = r1.findall("./period[@date='"+per2.get('date')+"']")
                if len(per1) == 1:
                    per1 = per1[0]
                    for typ2 in per2:
                        typ1 = per1.findall("./"+typ2.tag)
                        if len(typ1) == 1:
                            typ1 = typ1[0]
                            typ1.text = str(int(typ1.text) + int(typ2.text))
                        elif len(typ1) == 0:
                            per1.append(typ2)
                        else:
                            print "ERR : double element types in single period "
                elif len(per1) == 0:
                    r1.append(per2)
                elif len(per1) > 1:
                    print "ERR : multiple period hit in single participant"
                else:
                    print "ERR : strange..."
            r1.set('cnt', str(int(r1.get('cnt')) + int(r2.get('cnt'))))
            tail = r1.get('tail','empty')
            if tail == 'empty':
                r1.set('tail',two)
            else:
                r1.set('tail',two+tail)
            participants_root.remove(r2)
            print 'success'
        elif len(r1) == 0 and len(r2) == 1:
            r2[0].set('login',one)
            tail = r2[0].get('tail','empty')
            if tail == 'emty':
                r2[0].set('tail',two)
            else:
                r2[0].set('tail',two+tail)
            print 'WARNING there was no '+one+' so we just changed the name of '+two
        else:
            print 'ERR : false merge hit results : len(one) ' + str(len(r1)) + 'len(two)' + str(len(r2))
        print "MERGEPARTICIPANTS : donedone"
        self.participants_tree.write('data/' + self.org_name + '/participants.xml')
        return True

    # This method will transform the 'participants.xml' file to a 'weeklyrates.xml' file
    def transformWeeklyRates(self,reset,departure_weeks):
        if not os.path.exists('data/' + self.org_name + '/' + 'participants.xml'):
            print "participants.xml data file is missing!"
            exit()
        else:
            self.participants_tree = self.parseXml('participants.xml')
            participants_root = self.participants_tree.getroot()

        if not os.path.exists('data/' + self.org_name + '/' + 'weekly_rates.xml'):
                wr_tree = ET.ElementTree()
                el = ET.Element('root')
                wr_tree._setroot(el)
                wr_tree.write('data/' + self.org_name + '/' + 'weekly_rates.xml')
        else:
            wr_tree = ET.parse('data/' + self.org_name + '/' + 'weekly_rates.xml')
            if wr_tree.getroot().tag <> 'root':
                print "weekly_rates.xml is corrupt!"
                exit()
        wr_root = wr_tree.getroot()

        if wr_root.get('status') == 'done' and reset == False:
            print "Nothing to do here!"
            return True
        if reset == True:
            wr_root.clear()

        # find most recent contribution week (which was not a simple comment)
        last_contr_week = 0
        for participant in participants_root:
            for period in participant:
                for child in period:
                    if(child.tag != "comments"):
                        t = int(period.get('date'))
                        if t > last_contr_week:
                            last_contr_week = t


        for participant in participants_root:
            # discover first and last period of that participant and note it down as arrival and departure (if
            # conditions fulfilled
            min_period = 10000000
            max_period = 0
            for period in participant:
                z = int(period.get('date'))
                if z < min_period:
                    min_period = z
                if z > max_period:
                    max_period = z

            # check the identity of contributor
            identity_flag = 0 # 1 if developer, 0 if user/visitor
            for period in participant:
                if identity_flag == 0:
                    for child in period:
                        if(child.tag == 'commits' or child.tag == 'mergers'):
                            identity_flag = 1

            for period in participant:
                wr_period = wr_root.find("./period[@date='"+period.get('date')+"']")
                if wr_period == None:
                    wr_period = ET.SubElement(wr_root, 'period')
                    wr_period.set('date',period.get('date'))
                    r = ['arrivals','departures','commits','comments','mergers','pullrequests','issues','arrivals_user','arrivals_dev','departures_user','departures_dev']
                    for i in r:
                        x = ET.SubElement(wr_period, i)
                        x.text = '0'

                if int(period.get('date')) == min_period:
                    wr_arrivals = wr_period.find('arrivals')
                    wr_arrivals_user = wr_period.find('arrivals_user')
                    wr_arrivals_dev = wr_period.find('arrivals_dev')

                    if wr_arrivals is None:
                        print "transformWeeklyRates : Should not happen"
                        raise
                    wr_arrivals.text = str(int(wr_arrivals.text) + 1)
                    if identity_flag == 0:
                        wr_arrivals_user.text = str(int(wr_arrivals_user.text) + 1)
                    if identity_flag == 1:
                        wr_arrivals_dev.text = str(int(wr_arrivals_dev.text) + 1)

                if int(period.get('date')) == max_period and max_period <= last_contr_week - departure_weeks:
                    wr_departures = wr_period.find('departures')
                    wr_departures_user = wr_period.find('departures_user')
                    wr_departures_dev = wr_period.find('departures_dev')
                    if wr_departures is None:
                        print "transformWeeklyRates : Should not happen (bis)"
                        raise
                    wr_departures.text = str(int(wr_departures.text) + 1)
                    if identity_flag == 0:
                        wr_departures_user.text = str(int(wr_departures_user.text) + 1)
                    if identity_flag == 1:
                        wr_departures_dev.text = str(int(wr_departures_dev.text) + 1)

                r = ['commits','comments','mergers','pullrequests','issues']
                for i in r:
                    x = period.find(i)
                    if x is not None:
                        y = wr_period.find(i)
                        y.text = str(int(y.text)+int(x.text))
        wr_root.set('status','done')
        print "Done creating the weekly_rates file."
        wr_tree.write('data/' + self.org_name + '/' + 'weekly_rates.xml')

# DATA ENRICHMENT

    # This method will iterate through the participants list at the organisation level (participants.xml)
    # and enrich them with GitHub data
    def identifyParticipants(self):
        if not os.path.exists('data/' + self.org_name + '/' + 'participants.xml'):
                return False
        else:
            self.participants_tree = ET.parse('data/' + self.org_name + '/' + 'participants.xml')
            if self.participants_tree.getroot().tag <> 'root': exit()
        participants_root = self.participants_tree.getroot()

        self.g = []

        for login in self.logins:
            g = github.Github(login, self.passwords[self.logins.index(login)])
            self.g.append(g)

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
            self.participants_tree.write('data/' + self.org_name + '/participants.xml')
        participants_root.set('cnt',str(len(participants_root)))
        participants_root.set('identifyparticipants-status','completed')
        print "IDENTIFYPARTICIPANTS : donedone"
        self.participants_tree.write('data/' + self.org_name + '/participants.xml')
        return True

# DATA OUTPUT TO CVS

    # This method converts the data in a csv file. Each development action event is a data row with a
    # post- or pre-acquisition categorical variable.
    # It will only include profiles with a GitHub link.
    # Profile metadata (org, followers, following,...), time difference to acquisition week, and development action
    # type data, are added as columns
    def csvFullFillDevEventsRich(self):
        self.participants_tree = self.parseXml('participants.xml')
        participants_root = self.participants_tree.getroot()

        self.getAcqInfo()

        outfile = 'data/' + self.org_name + '/dev_events_data_rich.csv'

        #delete file if it exists
        try:
            os.remove(outfile)
        except OSError:
            pass

        with open(outfile, 'w') as csvfile:
            header = ['WEEK_NUMBER','acq_cat','before_acq','after_acq','acq_diff','LOGIN','followers','public_repos','tenure_weeks','int_cnt','acqg_org','acqd_org','TYPE','commits','comments','mergers','pullrequests','issues']
            csvwrite = csv.writer(csvfile)
            csvwrite.writerow(header)
            date_now = datetime.date(2016, 1, 3)
            acq_dt = iso_to_gregorian(int(str(self.acq_week)[:4]),int(str(self.acq_week)[4:]),1)
            for participant in participants_root:
                if participant.get('profile') == 'set':
                    LOGIN = participant.get('login')
                    followers = participant.get('followers')
                    public_repos = participant.get('public_repos')
                    date_created = datetime.datetime.strptime(participant.get('created_at'), "%Y-%m-%d").date()
                    diff = (date_now - date_created)
                    tenure_weeks = str(diff.days/7)
                    int_cnt = participant.get('cnt')

                    # many are part of both organisations, in that case we select the startup
                    acqg_org = 0
                    acqd_org = 0
                    st = participant.get('login')
                    options = ['login', 'blog','email', 'company', 'org', 'tail']
                    for x in options:
                        if participant.get(x) is not None:
                            st = st + participant.get(x)
                    # we also work with spaces elimination
                    st.lower()
                    if st.find(self.acqd_firm) <> -1:
                        acqd_org = 1
                    elif st.find(self.acqd_firm.replace(" ", "")) <> -1:
                        acqd_org = 1

                    if st.find(self.acqg_firm) <> -1:
                        acqg_org = 1
                    elif st.find(self.acqg_firm.replace(" ", "")) <> -1:
                        acqg_org = 1

                    for period in participant:
                        WEEK_NUMBER = period.get('date')
                        before_acq = 0
                        after_acq = 0
                        if int(WEEK_NUMBER) < self.acq_week:
                            acq_cat = 'before'
                            before_acq = 1
                        elif int(WEEK_NUMBER) > self.acq_week:
                            acq_cat = 'after'
                            after_acq = 1
                        elif int(WEEK_NUMBER) == self.acq_week:
                            acq_cat = 'during'
                        else:
                            print "CSV-FILE ERR : this shouldn't happen " + LOGIN + " " + WEEK_NUMBER
                            raise

                        # we assume 52 weeks per year.
                        event = iso_to_gregorian(int(WEEK_NUMBER[:4]),int(WEEK_NUMBER[4:]),1)
                        acq_diff = (event-acq_dt).days/7

                        for type in period:
                            commit = 0
                            merge = 0
                            pull_request = 0
                            comment = 0
                            issue = 0
                            if type.tag == 'commits':
                                TYPE = 'commit'
                                commit = 1
                            elif type.tag == 'mergers':
                                TYPE = 'merge'
                                merge = 1
                            elif type.tag == 'pullrequests':
                                TYPE = 'pull_request'
                                pull_request = 1
                            elif type.tag == 'comments':
                                TYPE = 'comment'
                                comment = 1
                            elif type.tag == 'issues':
                                TYPE = 'issue'
                                issue = 1
                            else:
                                continue
                            for i in range(int(type.text)):
                                csvwrite.writerow([WEEK_NUMBER,acq_cat,before_acq,after_acq,acq_diff,LOGIN,followers,public_repos,tenure_weeks,int_cnt,acqg_org,acqd_org,TYPE,commit,comment,merge,pull_request,issue])
                    #print "completed" + LOGIN
                else:
                    print "miss : " + participant.get('login')
        print "DONE with development events csv!"
        return True

    def csvFullFillDevEvents(self):
        self.participants_tree = self.parseXml('participants.xml')
        participants_root = self.participants_tree.getroot()

        self.getAcqInfo()

        outfile = 'data/' + self.org_name + '/dev_events_data.csv'

        #delete file if it exists
        try:
            os.remove(outfile)
        except OSError:
            pass

        with open(outfile, 'w') as csvfile:
            header = ['WEEK_NUMBER','acq_cat','before_acq','after_acq','acq_diff','LOGIN','int_cnt','TYPE','commits','comments','mergers','pullrequests','issues']
            csvwrite = csv.writer(csvfile)
            csvwrite.writerow(header)
            date_now = datetime.date(2016, 1, 3)
            acq_dt = iso_to_gregorian(int(str(self.acq_week)[:4]),int(str(self.acq_week)[4:]),1)
            for participant in participants_root:
                LOGIN = participant.get('login')
                int_cnt = participant.get('cnt')

                for period in participant:
                    WEEK_NUMBER = period.get('date')
                    before_acq = 0
                    after_acq = 0
                    if int(WEEK_NUMBER) < self.acq_week:
                        acq_cat = 'before'
                        before_acq = 1
                    elif int(WEEK_NUMBER) > self.acq_week:
                        acq_cat = 'after'
                        after_acq = 1
                    elif int(WEEK_NUMBER) == self.acq_week:
                        acq_cat = 'during'
                    else:
                        print "CSV-FILE ERR : this shouldn't happen " + LOGIN + " " + WEEK_NUMBER
                        raise

                    # we assume 52 weeks per year.
                    event = iso_to_gregorian(int(WEEK_NUMBER[:4]), int(WEEK_NUMBER[4:]), 1)
                    acq_diff = (event - acq_dt).days / 7

                    for type in period:
                        commit = 0
                        merge = 0
                        pull_request = 0
                        comment = 0
                        issue = 0
                        if type.tag == 'commits':
                            TYPE = 'commit'
                            commit = 1
                        elif type.tag == 'mergers':
                            TYPE = 'merge'
                            merge = 1
                        elif type.tag == 'pullrequests':
                            TYPE = 'pull_request'
                            pull_request = 1
                        elif type.tag == 'comments':
                            TYPE = 'comment'
                            comment = 1
                        elif type.tag == 'issues':
                            TYPE = 'issue'
                            issue = 1
                        else:
                            continue
                        for i in range(int(type.text)):
                            try:
                                csvwrite.writerow([WEEK_NUMBER, acq_cat, before_acq, after_acq, acq_diff, LOGIN, int_cnt, TYPE, commit, comment, merge, pull_request,issue])
                            except:
                                csvwrite.writerow([WEEK_NUMBER, acq_cat, before_acq, after_acq, acq_diff, 'surrogate_encodeERROR', int_cnt, TYPE, commit, comment, merge, pull_request,issue])
                            # print "completed" + LOGIN
        print "DONE with development events csv!"
        return True

    def csvFullFillWeeklyRates(self):
        wr_tree = self.parseXml('weekly_rates.xml')
        wr_root = wr_tree.getroot()

        self.getAcqInfo()
        outfile = 'data/' + self.org_name + '/weekly_rates_data.csv'

        #delete file if it exists
        try:
            os.remove(outfile)
        except OSError:
            pass

        with open(outfile, 'w') as csvfile:
            header = ['WEEK_NUMBER','acq_cat','before_acq','after_acq','acq_diff','arrivals','departures','commits','comments','mergers','pullrequests','issues','arrivals_user','arrivals_dev','departures_user','departures_dev']
            csvwrite = csv.writer(csvfile)
            csvwrite.writerow(header)
            date_now = datetime.date(2016, 1, 3)
            acq_dt = iso_to_gregorian(int(str(self.acq_week)[:4]),int(str(self.acq_week)[4:]),1)
            for period in wr_root:
                WEEK_NUMBER = period.get('date')
                before_acq = 0
                after_acq = 0
                if int(WEEK_NUMBER) < self.acq_week:
                    acq_cat = 'before'
                    before_acq = 1
                elif int(WEEK_NUMBER) > self.acq_week:
                    acq_cat = 'after'
                    after_acq = 1
                elif int(WEEK_NUMBER) == self.acq_week:
                    acq_cat = 'during'
                else:
                    print "CSV-FILE ERR : this shouldn't happen " + WEEK_NUMBER
                    raise

                event = iso_to_gregorian(int(WEEK_NUMBER[:4]), int(WEEK_NUMBER[4:]), 1)
                acq_diff = (event - acq_dt).days / 7

                csvwrite.writerow([WEEK_NUMBER,acq_cat,before_acq,after_acq,acq_diff,period.find('arrivals').text,period.find('departures').text,period.find('commits').text,period.find('comments').text,period.find('mergers').text,period.find('pullrequests').text,period.find('issues').text,period.find('arrivals_user').text,period.find('arrivals_dev').text,period.find('departures_user').text,period.find('departures_dev').text])

            if self.org_name == 'feedhenry':
                csvwrite.writerow(['201450','after','0','1','10','0','0','0','0','0','0','0','0','0','0','0'])
                csvwrite.writerow(['201341','before','1','0','-51','0','0','0','0','0','0','0','0','0','0','0'])
                csvwrite.writerow(['201342','before','1','0','-50','0','0','0','0','0','0','0','0','0','0','0'])
                csvwrite.writerow(['201452','after','0','1','12','0','0','0','0','0','0','0','0','0','0','0'])
                csvwrite.writerow(['201501','after','0','1','13','0','0','0','0','0','0','0','0','0','0','0'])
                csvwrite.writerow(['201352','before','1','0','-40','0','0','0','0','0','0','0','0','0','0','0'])
                csvwrite.writerow(['201506','after','0','1','18','0','0','0','0','0','0','0','0','0','0','0'])
            if self.org_name == 'fusesource':
                csvwrite.writerow(['201152','before','1','0','-26','0','0','0','0','0','0','0','0','0','0','0'])
                csvwrite.writerow(['201220','before','1','0','-6','0','0','0','0','0','0','0','0','0','0','0'])


        print "DONE with weekly rates csv!"
        return True

# UTILITY

    # This method will count some key stats that summarizes the organisation.
    # The flag triggers a calculation of the development actions breakdown
    def activityStats(self, flag):
        self.participants_tree = self.parseXml('participants.xml')
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
        participants_root.set('totalCnt',str(cnt_all_act))
        self.participants_tree.write('data/' + self.org_name + '/' + 'participants.xml')
        print "----------------------\n Contributor Stats \n \n"
        print "# Total Participants : "+str(cnt_all)
        s = '%.2f'%(float(cnt_GitHub)/float(cnt_all)*100)
        r = '%.2f'%(float(cnt_GitHub_act)/float(cnt_all_act)*100)
        print "# GitHub participants : "+str(cnt_GitHub)+" ("+s+"%)"
        print "# Developers : "+str(cnt_dev)
        print "# GitHub Developers (post-script) : "+str(cnt_dev_GitHub)
        print "# Total development actions : "+str(cnt_all_act)
        print "# Development actions linked to GitHub account : "+str(cnt_GitHub_act)+" ("+r+"%)"


        if flag == True:
            print "\n----------------------\n Development Breakdown \n \n"
            r = '%.2f'%(float(cnt_commits)/float(cnt_all_act)*100)
            print "# Commits : "+str(cnt_commits)+" ("+r+"%)"
            r = '%.2f'%(float(cnt_comments)/float(cnt_all_act)*100)
            print "# Comments : "+str(cnt_comments)+" ("+r+"%)"
            r = '%.2f'%(float(cnt_mergers)/float(cnt_all_act)*100)
            print "# Mergers : "+str(cnt_mergers)+" ("+r+"%)"
            r = '%.2f'%(float(cnt_pullrequests)/float(cnt_all_act)*100)
            print "# Pull Requests : "+str(cnt_pullrequests)+" ("+r+"%)"
            r = '%.2f'%(float(cnt_issues)/float(cnt_all_act)*100)
            print "# Issues : "+str(cnt_issues)+" ("+r+"%)"
        return True

    # Open a xml file in the Organisation folder
    def parseXml(self, filename):
        if not os.path.exists('data/' + self.org_name + '/' + filename):
            tree = ET.ElementTree()
            el = ET.Element('root')
            tree._setroot(el)
            tree.write('data/' + self.org_name + '/' + filename)
        else:
            tree = ET.parse('data/' + self.org_name + '/' + filename)
            if tree.getroot().tag <> 'root': exit()
        return tree

    def getAcqInfo(self):
        self.participants_tree = self.parseXml('participants.xml')
        participants_root = self.participants_tree.getroot()
        # read some stuff, ask to the user if they don't exist and then write them
        flag = 0
        try:
            self.acq_week = int(participants_root.get('acq_week'))
            print "The acquisition took place on " + str(self.acq_week)
        except:
            print self.org_name + " : Please give in the acquisition week number in the following format 'YYYYWW' according to ISO week numbers."
            self.acq_week = int(raw_input())
            participants_root.set('acq_week',str(self.acq_week))
            flag = 1
        try:
            self.acqg_firm = participants_root.get('acqg_firm')
            print "The acquiring firm is " + self.acqg_firm
        except:
            print self.org_name + " : Please give in the name of the acquiring firm : "
            self.acqg_firm = raw_input()
            participants_root.set('acqg_firm',self.acqg_firm.lower())
            flag = 1
        try:
            self.acqd_firm = participants_root.get('acqd_firm')
            print "The acquired firm is " + self.acqd_firm
        except:
            print self.org_name + " : Please give in the name of the acquired firm : "
            self.acqd_firm = raw_input()
            participants_root.set('acqd_firm',self.acqd_firm.lower())
            flag = 1
        if flag == 1:
            self.participants_tree.write('data/' + self.org_name + '/' + 'participants.xml')

# STATIC FUNCTIONS

def iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    fifth_jan = datetime.date(iso_year, 1, 5)
    _, fifth_jan_week, fifth_jan_day = fifth_jan.isocalendar()
    return fifth_jan + datetime.timedelta(days=iso_day-fifth_jan_day, weeks=iso_week-fifth_jan_week)