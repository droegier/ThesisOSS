# Main
main <- function() {
  y <- c('pydata','pentaho','rabbitmq','tutumcloud','ansible','spree','sequenceiq','thinkaurelius','feedhenry','Elgg','wiredtiger','ceph','eucalyptus','gluster','fusesource','NuCivic','pydata','pentaho','rabbitmq')
  
  #makeRegWRtable('departures',y)
  #makeRegWRtable('arrivals',y)
  #makeRegWRtable('non_technical_contributions',y)
  #makeRegWRtable('technical_contributions',y)
  #makeRegWRtable('all_contributions',y)
  
  
  makeWRtable('departures',y)
  makeWRtable('departures_user',y)
  makeWRtable('departures_dev',y)
  makeWRtable('arrivals',y)
  makeWRtable('arrivals_user',y)
  makeWRtable('arrivals_dev',y)
  #makeWRtable('commits',y)
  #makeWRtable('mergers',y)
  #makeWRtable('comments',y)
  
  makeWRtable('non_technical_contributions',y)
  makeWRtable('technical_contributions',y)
  makeWRtable('all_contributions',y)
  
  #makeDEtable('',y)
}

##########################################################
# CALCULATE INTER-ACTION TIMES

intertime <- function() {
  inter <- read.csv("~/Google Drive/Academic/ETH Zurich/Thesis/Python GitHub/code/data/inter_action_time.csv")
  plot(ecdf(inter$X17),xlab = "Number of Weeks",ylab = "Cum. Dens. of ICT",xlim=c(15,20),ylim=c(0.9,1))
  abline(0.95,0,col="green")
}

##########################################################
# FUNCTIONS FOR LOOKING AT DEVELOPMENT ACTIONS AS EVENTS (LOGIT)

makeDEtable <- function(filter,orgs) {
  out <- matrix(c(filter,"","",""),nrow=1,ncol=4)
  for(i in 1:length(orgs)) {
    out <- rbind(out,matrix(c(orgs[i],"","",""),nrow=1,ncol=4))
    out <- rbind(out,summary.glm(singleDEorg(filter,orgs[i]))$coefficients)
  }
  x <- paste("~/Google Drive/Academic/ETH Zurich/Thesis/R Workspace/de_",filter,".csv",sep="")
  write.csv(out,file = x)
}

singleDEorg <- function(filter,DEname) {
  DEdata <- retrieveDEdata(DEname)
  DEdata <- cutData(DEdata)
  if(filter == "commits") {
    DEdata <- subset(DEdata,DEdata['commits']==1)
  }
  else if(filter == "comments") {
    DEdata <- subset(DEdata,DEdata['comments']==1)
  }
  else if(filter == "pullrequests") {
    DEdata <- subset(DEdata,DEdata['pullrequests']==1)
  }
  else if(filter == "mergers") {
    DEdata <- subset(DEdata,DEdata['mergers']==1)
  }
  else if(filter == "issues") {
    DEdata <- subset(DEdata,DEdata['issues']==1)
  }
  else if(filter == "technical_contributions") {
    DEdata <- subset(DEdata,DEdata['commits']==1 | DEdata['merges']==1)
  }
  else if(filter == "non_technical_contributions") {
    DEdata <- subset(DEdata,DEdata['issues']==1 | DEdata['pullrequests']==1 | DEdata['comments']==1)
  }
  DElogit <- logitOnDE(DEdata)
  return(DElogit)
}

# Retrieve developepment action events csv file
retrieveDEdata <- function(name) {
  file <- paste("~/Google Drive/Academic/ETH Zurich/Thesis/Python GitHub/code/data/",name,"/dev_events_data.csv",sep="")
  data_de <- read.csv(file)
  return(data_de)
}

logitOnDE <- function(DEdata) {
  logit_all <- glm(after_acq ~ followers + public_repos + tenure_weeks + int_cnt + acqg_org + acqd_org,family=binomial(link='logit'),data=DEdata)
}

##########################################################
# FUNCTIONS FOR LOOKING AT DEVELOPMENT ACTIONS IN WEEKLY RATES (ANOVA)

makeWRtable <- function(variable_name,orgs) {
  out <- matrix(c(variable_name,"mean before","mean after","F value","p value"),nrow=1,ncol=5)
  if(variable_name=='technical_contributions' | variable_name=='non_technical_contributions' | variable_name=='all_contributions') {
    for(i in 1:length(orgs))
    {
      #out <- rbind(out,matrix(c(orgs[i],"","","",""),nrow=1,ncol=5))
      out <- rbind(out,combWRorg(orgs[i],variable_name))
    }
  }
  else {
    for(i in 1:length(orgs))
    {
      #out <- rbind(out,matrix(c(orgs[i],"","","",""),nrow=1,ncol=5))
      out <- rbind(out,singleWRorg(orgs[i],variable_name))
    }
  }

  x <- paste("~/Google Drive/Academic/ETH Zurich/Thesis/R Workspace/wr_",variable_name,".csv",sep="")
  write.csv(out,file = x)
}

combWRorg <- function(WRname,variable_name) {
  WRdata <- retrieveWRdata(WRname)
  WRdata <- cutData(WRdata)
  if(variable_name=='technical_contributions') {
    WRdata$technical_contributions <- WRdata$commits + WRdata$mergers
  }
  else if(variable_name=='non_technical_contributions') {
    WRdata$non_technical_contributions <- WRdata$issues + WRdata$comments + WRdata$pullrequests
  }
  else if(variable_name=='all_contributions') {
    WRdata$all_contributions <- WRdata$issues + WRdata$comments + WRdata$pullrequests + WRdata$commits + WRdata$mergers
  }
  WRdataAfter <- subset(WRdata,after_acq==1)
  WRdataBefore <- subset(WRdata,after_acq==0)
  setAfter <- mean(WRdataAfter[,variable_name])
  setBefore <- mean(WRdataBefore[,variable_name])
  
  WRanova <- anovaOnWR(WRdata,variable_name)
  ret <- matrix(c(WRname, setBefore, setAfter, summary(WRanova)[[1]]$'F value'[1],summary(WRanova)[[1]]$'Pr(>F)'[1]),nrow=1,ncol=5)
  return(ret)
} 

singleWRorg <- function(WRname,variable_name) {
  WRdata <- retrieveWRdata(WRname)
  WRdata <- cutData(WRdata)
  WRdataAfter <- subset(WRdata,after_acq==1)
  WRdataBefore <- subset(WRdata,after_acq==0)
  setAfter <- mean(WRdataAfter[,variable_name])
  setBefore <- mean(WRdataBefore[,variable_name])
  
  WRanova <- anovaOnWR(WRdata,variable_name)
  ret <- matrix(c(WRname, setBefore, setAfter,summary(WRanova)[[1]]$'F value'[1], summary(WRanova)[[1]]$'Pr(>F)'[1]),nrow=1,ncol=5)
  
  
  #WRcorrelation <- cor(WRdata['after_acq'],WRdata[variable_name], method="pearson")
  #ret <- matrix(c('pvalue', summary(WRanova)[[1]]$'Pr(>F)'[1], 'coef', WRanova$coefficients[2]),nrow=1,ncol=4)
  return(ret)
}

# Retrieve weekly rates csv file
retrieveWRdata <- function(name) {
  file <- paste("~/Google Drive/Academic/ETH Zurich/Thesis/Python GitHub/code/data/",name,"/weekly_rates_data.csv",sep="")
  data_wr <- read.csv(file)
  return(data_wr)
}

anovaOnWR <- function(data_input,variable_name) {
  attach(data_input)
  x <- as.integer(unlist(data_input[variable_name]))
  anovaResult <- aov( x ~ after_acq )
  detach()
  return(anovaResult)
}

##########################################################
# FUNCTIONS FOR LOOKING AT DEVELOPMENT ACTIONS IN WEEKLY RATES (REGRESSION)

makeRegWRtable <- function(variable_name,orgs) {
  out <- matrix(c(variable_name,"","",""),nrow=1,ncol=4)
  if(variable_name=='technical_contributions' | variable_name=='non_technical_contributions' | variable_name=='all_contributions') {
    for(i in 1:length(orgs))
    {
      out <- rbind(out,matrix(c(orgs[i],"","",""),nrow=1,ncol=4))
      out <- rbind(out,combRegWRorg(orgs[i],variable_name))
    }
  }
  else if (variable_name=='arrivals' | variable_name=='departures' | variable_name=='commits' | variable_name=='comments' | variable_name=='mergers' | variable_name=='pullrequests' | variable_name=='issues') {
    for(i in 1:length(orgs))
    {
      out <- rbind(out,matrix(c(orgs[i],"","",""),nrow=1,ncol=4))
      out <- rbind(out,singleRegWRorg(orgs[i],variable_name))
    }
  }
  else {
    return('ERROR')
  }
  x <- paste("~/Google Drive/Academic/ETH Zurich/Thesis/R Workspace/wr_reg_",variable_name,".csv",sep="")
  write.csv(out,file = x)
}

combRegWRorg <- function(WRname,variable_name) {
  WRdata <- retrieveWRdata(WRname)
  WRdata <- cutData(WRdata)
  if(variable_name=='technical_contributions') {
    WRdata$technical_contributions <- WRdata$commits + WRdata$mergers
  }
  else if(variable_name=='non_technical_contributions') {
    WRdata$non_technical_contributions <- WRdata$issues + WRdata$comments + WRdata$pullrequests
  }
  else if(variable_name=='all_contributions') {
    WRdata$all_contributions <- WRdata$issues + WRdata$comments + WRdata$pullrequests + WRdata$commits + WRdata$mergers
  }
  #WRdataAfter <- subset(WRdata,after_acq==1)
  #WRdataBefore <- subset(WRdata,after_acq==0)
  #setAfter <- mean(WRdataAfter[,variable_name])
  #setBefore <- mean(WRdataBefore[,variable_name])
  
  WRreg <- regOnWR(WRdata,variable_name)
  ret <- matrix(c('','','',''),nrow=1,ncol=4)
  return(ret)
}

singleRegWRorg <- function(WRname,variable_name) {
  WRdata <- retrieveWRdata(WRname)
  WRdata <- cutData(WRdata)
  #WRdataAfter <- subset(WRdata,after_acq==1)
  #WRdataBefore <- subset(WRdata,after_acq==0)
  #setAfter <- mean(WRdataAfter[,variable_name])
  #setBefore <- mean(WRdataBefore[,variable_name])
  
  WRreg <- regOnWR(WRdata,variable_name)
  ret <- matrix(c('', '','',''),nrow=1,ncol=4)

  return(ret)
}

regOnWR <- function(data_input,variable_name) {
  
  anovaResult <- lm(paste(variable_name,' ~ after_acq + acq_diff',data=data_input))
  
  return(anovaResult)
}

##############################################
# SHARED FUNCTIONS

cutData <- function(temp) {
  # eliminate the 'during' category of 
  temp <- subset(temp,acq_cat!='during')
  
  # eliminate activity that takes place outside a one year radius from the acquisition event
  temp <- subset(temp,acq_diff>-53 & acq_diff<53)
  
  # cut the data for symmetric periods around acquisition
  # CHECK THIS make sure to not include maximum boundary periods that only have comments (this is to fix a problem in the data collection)
  #help <- temp[temp$commit != 0, ]
  #max_w <- max(help$acq_diff,na.rm=TRUE)
  max_w <- max(temp$acq_diff,na.rm=TRUE)
  min_w <- min(temp$acq_diff,na.rm=TRUE)
  res <- min(max_w,-min_w)
  temp <- subset(temp,acq_diff>-res-1 & acq_diff<res+1)
}
