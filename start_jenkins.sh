#!/bin/zsh
export JENKINS_HOME="/Users/admin/jenkins_data"
cd /Users/admin/jenkins_portable
exec /usr/bin/java -jar jenkins.war --httpPort=8080
