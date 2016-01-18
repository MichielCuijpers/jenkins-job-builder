# -*- coding: utf-8 -*-
# Copyright (C) 2015 Joost van der Griendt <joostvdg@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""
The workflow Project module handles creating Jenkins workflow projects.
You may specify ``workflow`` in the ``project-type`` attribute of
the :ref:`Job` definition.

You can add an SCM with the script-path, but for now only GIT is supported.

Requires the Jenkins :jenkins-wiki:`Workflow Plugin <Workflow+Plugin>`.

In order to use it for job-template you have to escape the curly braces by
doubling them in the script: { -> {{ , otherwise it will be interpreted by the
python str.format() command.

:Job Parameters:
    * **timer-trigger** (`str`): The timer spec for when the jobs should be triggered.
    * **env-properties** (`str`): Environment variables. (optional)
    * **periodic-folder-spec** (`str`): The timer spec for when the repository should be checked for branches.
    * **periodic-folder-interval** (`str`): Interval for when the folder should be checked.
        Not sure yet how the two related.
    * **prune-dead-branches** (`str`): If dead branches upon check should result in their job being dropped.
        (defaults to true) (optional)
    * **number-to-keep** (`str`): How many builds should be kept. (defaults to -1, all) (optional)
    * **days-to-keep** (`str`): For how many days should a build be kept. (defaults to -1, forever) (optional)
    * **scm** (`str`): The SCM definition.
    * **git** (`str`): Currently only GIT as SCM is supported, use this as sub-structure of scm.
    * **url** (`str`): The GIT URL.
    * **credentials-id** (`str`): The credentialsId to use to connect to the GIT URL.
    * **includes** (`str`): Which branches should be included. (defaults to *, all)  (optional)
    * **excludes** (`str`): Which branches should be excluded. (defaults to empty, none)  (optional)
    * **ignore-on-push-notifications** (`bool`): If a job should not trigger upon push notifications.
        (defaults to false) (optional)
    * **publisher-white-list** (`str`): A list of which publisher plugins should be whitelisted.
        (fully qualified name) (optional)


Job with inline script example:

    .. literalinclude::
      /../../tests/yamlparser/fixtures/project_workflow_multibranch_template001.yaml

"""
import logging
import xml.etree.ElementTree as XML
import jenkins_jobs.modules.base

logger = logging.getLogger(str(__name__))


class WorkflowMultiBranch(jenkins_jobs.modules.base.Base):
    sequence = 0

    def root_xml(self, data):
        xml_parent = XML.Element('org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject')
        xml_parent.attrib['plugin'] = 'workflow-multibranch'

        if 'multibranch' not in data:
            return xml_parent

        project_def = data['multibranch']

        properties = XML.SubElement(xml_parent, 'properties')
        folder_credentials_provider = XML.SubElement(properties, 'com.cloudbees.hudson.plugins.folder.properties.FolderCredentialsProvider_-FolderCredentialsProperty')
        folder_credentials_provider.attrib['plugin'] = 'cloudbees-folder'
        entry = XML.SubElement(folder_credentials_provider, 'entry')
        domain = XML.SubElement(entry, 'com.cloudbees.plugins.credentials.domains.Domain')
        XML.SubElement(domain, 'specifications')

        if 'env-properties' in data['multibranch']:
            env_properties_parent = XML.SubElement(properties, 'com.cloudbees.hudson.plugins.folder.properties.EnvVarsFolderProperty')
            env_properties_parent.attrib['plugin'] = 'cloudbees-folders-plus'
            env_properties = XML.SubElement(env_properties_parent, 'properties')
            env_properties.text = project_def['env-properties']

        orphaned_item_strategy = XML.SubElement(xml_parent, 'orphanedItemStrategy')
        orphaned_item_strategy.attrib['class'] = 'com.cloudbees.hudson.plugins.folder.computed.DefaultOrphanedItemStrategy'
        orphaned_item_strategy.attrib['plugin'] = 'cloudbees-folder'

        if 'prune-dead-branches' in data['multibranch']:
            prune_dead_branches = data['multibranch'].get('prune-dead-branches', False)
            XML.SubElement(orphaned_item_strategy, 'pruneDeadBranches').text = str(prune_dead_branches).lower()

        XML.SubElement(orphaned_item_strategy, 'daysToKeep').text = project_def.get('days-to-keep', '-1')
        XML.SubElement(orphaned_item_strategy, 'numToKeep').text = project_def.get('number-to-keep', '-1')

        triggers = XML.SubElement(xml_parent, 'triggers')
        if 'timer-trigger' in data['multibranch']:
            timer_trigger = XML.SubElement(triggers, 'hudson.triggers.TimerTrigger')
            XML.SubElement(timer_trigger, 'spec').text = project_def['timer-trigger']

        periodic_folder_trigger = XML.SubElement(triggers, 'com.cloudbees.hudson.plugins.folder.computed.PeriodicFolderTrigger')
        periodic_folder_trigger.attrib['plugin'] = 'cloudbees-folder'
        XML.SubElement(periodic_folder_trigger, 'spec').text = project_def['periodic-folder-spec']
        XML.SubElement(periodic_folder_trigger, 'interval').text = project_def['periodic-folder-interval']

        sources = XML.SubElement(xml_parent, 'sources')
        sources.attrib['class'] = 'jenkins.branch.MultiBranchProject$BranchSourceList'
        sources.attrib['plugin'] = 'branch-api'
        sources_data = XML.SubElement(sources, 'data')
        branch_source = XML.SubElement(sources_data, 'jenkins.branch.BranchSource')

        if 'scm' in project_def:
            scm = project_def['scm']
            if 'git' in scm:
                git = scm['git']
                source = XML.SubElement(branch_source, 'source')
                source.attrib['class'] = 'jenkins.plugins.git.GitSCMSource'
                source.attrib['plugin'] = 'git'
                # What to do with this? XML.SubElement(source, 'id').text = '3c759f39-3118-4bb2-bbf9-e997028ae98f'
                XML.SubElement(source, 'remote').text = git['url']
                XML.SubElement(source, 'credentialsId').text = git['credentials-id']
                XML.SubElement(source, 'includes').text = git.get('includes', '*')
                if 'excludes' in git:
                    XML.SubElement(source, 'excludes').text = git['excludes']
                else:
                    XML.SubElement(source, 'excludes')

                ignore_on_push = git.get('ignore-on-push-notifications', True)
                XML.SubElement(source, 'ignoreOnPushNotifications').text = str(ignore_on_push).lower()

        strategy = XML.SubElement(branch_source, 'strategy')
        strategy.attrib['class'] = 'jenkins.branch.DefaultBranchPropertyStrategy'

        if 'publisher-white-list' in project_def:
            whitelist_properties = XML.SubElement(strategy, 'properties')
            whitelist_properties.attrib['class'] = 'java.util.Arrays$ArrayList'
            whitelist_a = XML.SubElement(whitelist_properties, 'a')
            whitelist_a.attrib['class'] = 'jenkins.branch.BranchProperty-array'
            untrusted_branch_property = XML.SubElement(whitelist_a, 'jenkins.branch.UntrustedBranchProperty')
            whitelist = XML.SubElement(untrusted_branch_property, 'publisherWhitelist')
            whitelist.attrib['class'] = 'sorted-set'

            for publisher in project_def['publisher-white-list']:
                XML.SubElement(whitelist, 'string').text = publisher

        factory = XML.SubElement(xml_parent, 'factory')
        factory_owner = XML.SubElement(factory, 'strategy')
        factory_owner.attrib['class'] = 'org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject'
        factory_owner.attrib['reference'] = "../.."

        return xml_parent
