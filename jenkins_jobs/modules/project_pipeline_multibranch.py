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
  * **timer-trigger** (`str`): The timer spec for when the jobs
   should be triggered.
  * **env-properties** (`str`): Environment variables. (optional)
  * **periodic-folder-spec** (`str`): The timer spec for when
   repository should be checked for branches.
  * **periodic-folder-interval** (`str`): Interval for when the folder
   should be checked.
  * **prune-dead-branches** (`str`): If dead branches upon check
   should result in their job being dropped. (defaults to true) (optional)
  * **number-to-keep** (`str`): How many builds should be kept.
   (defaults to -1, all) (optional)
  * **days-to-keep** (`str`): For how many days should a build be kept.
   (defaults to -1, forever) (optional)
  * **scm** (`str`): The SCM definition.
  * **git** (`str`): Currently only GIT as SCM is supported,
   use this as sub-structure of scm.
  * **url** (`str`): The GIT URL.
  * **credentials-id** (`str`): The credentialsId to use to connect to the GIT
   repository URL.
  * **includes** (`str`): Which branches should be included.
    (defaults to *, all)  (optional)
  * **excludes** (`str`): Which branches should be excluded.
    (defaults to empty, none)  (optional)
  * **ignore-on-push-notifications** (`bool`): If a job should not trigger upon
    push notifications. (defaults to false) (optional)
  * **publisher-white-list** (`str`): A list of which publisher plugins
    should be whitelisted. (fully qualified name) (optional)


Job with inline script example:

    .. literalinclude::
      /../../tests/yamlparser/fixtures/project_pipeline_multibranch_template001.yaml

"""
import logging
import uuid
import xml.etree.ElementTree as XML
import jenkins_jobs.modules.base
from scm import git

logger = logging.getLogger(str(__name__))


class PipelineMultiBranch(jenkins_jobs.modules.base.Base):
    """
        Project type for the Jenkins Multi-Branch Pipeline plugin.
    """
    sequence = 0

    def root_xml(self, data):
        """
            Builds up the Jenkins config.xml for this project type.
        """
        xml_parent = XML.Element('org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject')
        xml_parent.attrib['plugin'] = 'workflow-multibranch'

        if 'multibranch' not in data:
            return xml_parent

        project_def = data['multibranch']

        properties = XML.SubElement(xml_parent, 'properties')
        folder_credentials_provider = XML.SubElement(properties,
                                                     'com.cloudbees.hudson.plugins.folder.properties.FolderCredentialsProvider_-FolderCredentialsProperty')
        folder_credentials_provider.attrib['plugin'] = 'cloudbees-folder'
        domain_credentials_map = XML.SubElement(folder_credentials_provider, 'domainCredentialsMap')
        domain_credentials_map.attrib['class'] = 'hudson.util.CopyOnWriteMap$Hash'
        entry = XML.SubElement(domain_credentials_map, 'entry')
        domain = XML.SubElement(entry,
                                'com.cloudbees.plugins.credentials.domains.Domain')
        domain.attrib['plugin'] = 'credentials'
        XML.SubElement(domain, 'specifications')
        XML.SubElement(entry, 'java.util.concurrent.CopyOnWriteArrayList')

        if 'env-properties' in data['multibranch']:
            env_properties_parent = XML.SubElement(properties,
                                                   'com.cloudbees.hudson.plugins.folder.properties.EnvVarsFolderProperty')
            env_properties_parent.attrib['plugin'] = 'cloudbees-folders-plus'
            env_properties = XML.SubElement(env_properties_parent, 'properties')
            env_properties.text = project_def['env-properties']

        views = XML.SubElement(xml_parent, 'views')
        allView = XML.SubElement(views, 'hudson.model.AllView')
        owner = XML.SubElement(allView, 'owner')
        owner.attrib['class'] = 'org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject'
        owner.attrib['reference'] = '../../..'
        all_view_name = XML.SubElement(allView, 'name')
        all_view_name.text = 'All'
        all_view_filter_executors = XML.SubElement(allView, 'filterExecutors')
        all_view_filter_executors.text = 'false'
        all_view_filter_queue = XML.SubElement(allView, 'filterQueue')
        all_view_filter_queue.text = 'false'
        all_view_properties = XML.SubElement(allView, 'properties')
        all_view_properties.attrib['class'] = 'hudson.model.View$PropertyList'

        views_tab_bar = XML.SubElement(xml_parent, 'viewsTabBar')
        views_tab_bar.attrib['class'] = 'hudson.views.DefaultViewsTabBar'

        health_metrics = XML.SubElement(xml_parent, 'healthMetrics')
        health_metrics_plugin = XML.SubElement(health_metrics,
                                               'com.cloudbees.hudson.plugins.folder.health.WorstChildHealthMetric')
        health_metrics_plugin.attrib['plugin'] = 'cloudbees-folder'

        icon = XML.SubElement(xml_parent, 'icon')
        icon.attrib['class'] = 'com.cloudbees.hudson.plugins.folder.icons.StockFolderIcon'
        icon.attrib['plugin'] = 'cloudbees-folder'

        orphaned_item_strategy = XML.SubElement(xml_parent, 'orphanedItemStrategy')
        orphaned_item_strategy.attrib['class'] = 'com.cloudbees.hudson.plugins.folder.computed.DefaultOrphanedItemStrategy'
        orphaned_item_strategy.attrib['plugin'] = 'cloudbees-folder'

        if 'prune-dead-branches' in data['multibranch']:
            prune_dead_branches = data['multibranch'].get('prune-dead-branches', False)
            XML.SubElement(orphaned_item_strategy,
                           'pruneDeadBranches').text = str(prune_dead_branches).lower()

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
        # TODO add multiple sources from scm
        # For each git repo, there should be a BranchSource

        if 'scm' in project_def:
            for git_data in project_def['scm']:
                logger.warn('git_data = %s' % git_data)
                if isinstance(git_data, dict) and 'git' in git_data:
                    branch_source = XML.SubElement(
                        sources_data, 'jenkins.branch.BranchSource')
                    self.generate_git_scm_xml(branch_source, git_data['git'])

                    if 'strategy' in git_data['git']:
                        self.generate_source_strategy(branch_source, git_data['git']['strategy'])
                    else:
                        self.generate_default_source_strategy(branch_source)
                else:
                    logger.warn('We cannot process scm')

        owner = XML.SubElement(sources, 'owner')
        owner.attrib['class'] = 'org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject'
        owner.attrib['reference'] = '../..'

        factory = XML.SubElement(xml_parent, 'factory')
        factory.attrib['class'] = 'org.jenkinsci.plugins.workflow.multibranch.WorkflowBranchProjectFactory'
        factory_owner = XML.SubElement(factory, 'owner')
        factory_owner.attrib['class'] = 'org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject'
        factory_owner.attrib['reference'] = '../..'

        return xml_parent

    def generate_git_scm_xml(self, xml_parent, data):
        """
        """
        git_source = XML.SubElement(xml_parent, 'source')
        git_source.attrib['class'] = 'jenkins.plugins.git.GitSCMSource'
        git_source.attrib['plugin'] = 'git'

        ignore_on_push = data.get('ignore-on-push-notifications', True)

        git_element_list = []
        git_element_list.append(['id', str(uuid.uuid4())])
        git_element_list.append(['remote', data['url']])
        git_element_list.append(['credentialsId', data['credentials-id']])
        git_element_list.append(['ignoreOnPushNotifications', str(ignore_on_push).lower()])
        git_element_list.append(['includes', data.get('includes', '*')])

        if 'excludes' in data:
            git_element_list.append(['excludes', data['excludes']])
        else:
            XML.SubElement(git_source, 'excludes')

        for item in git_element_list:
            XML.SubElement(git_source, item[0]).text = item[1]

        # add extensions
        temp_xml = XML.SubElement(git_source, 'temp-git')
        git(self, temp_xml, data)
        temp_xml_scm = temp_xml.find('scm')
        if temp_xml_scm and temp_xml_scm.find('extensions'):
            temp_extensions = temp_xml_scm.find('extensions')
            git_source.append(temp_extensions)
        git_source.remove(temp_xml)

    def generate_default_source_strategy(self, xml_parent):
        """
        """
        strategy = XML.SubElement(xml_parent, 'strategy')
        strategy.attrib['class'] = 'jenkins.branch.DefaultBranchPropertyStrategy'
        strategy_properties = XML.SubElement(strategy, 'properties')
        strategy_properties.attrib['class'] = 'empty-list'

    def generate_source_strategy(self, xml_parent, data):
        """
        """
        if 'exceptions' in data:
            logger.warn('contains git strategy exceptions')
            strategy = XML.SubElement(xml_parent, 'strategy')
            strategy.attrib['class'] = 'jenkins.branch.NamedExceptionsBranchPropertyStrategy'

            # defaultPropeties section
            strategy_properties = XML.SubElement(strategy, 'defaultProperties')
            strategy_properties.attrib['class'] = 'java.util.Arrays$ArrayList'
            prop_a = XML.SubElement(strategy_properties, 'a')
            prop_a.attrib['class'] = 'jenkins.branch.BranchProperty-array'
            XML.SubElement(prop_a, 'jenkins.branch.NoTriggerBranchProperty')

            named_exceptions = XML.SubElement(strategy, 'namedExceptions')
            named_exceptions.attrib['class'] = 'java.util.Arrays$ArrayList'
            named_exceptions_a = XML.SubElement(named_exceptions, 'a')
            named_exceptions_a.attrib['class'] = 'jenkins.branch.NamedExceptionsBranchPropertyStrategy$Named-array'

            for exception in data['exceptions']:
                logger.warn('Exception found for branch %s' % exception)
                named_exception = XML.SubElement(named_exceptions_a, 'jenkins.branch.NamedExceptionsBranchPropertyStrategy_-Named')
                named_exception_props = XML.SubElement(named_exception, 'props')
                named_exception_props.attrib['class'] = 'java.util.Arrays$ArrayList'
                named_exception_props_a = XML.SubElement(named_exception_props, 'a')
                named_exception_props_a.attrib['class'] = 'jenkins.branch.BranchProperty-array'
                XML.SubElement(named_exception_props_a, 'jenkins.branch.NoTriggerBranchProperty')
                exception_branch_name = XML.SubElement(named_exception, 'name')
                exception_branch_name.text = exception
        else:
            logger.warn('contains simple git strategy')
            strategy = XML.SubElement(xml_parent, 'strategy')
            strategy.attrib['class'] = 'jenkins.branch.DefaultBranchPropertyStrategy'
            strategy_properties = XML.SubElement(strategy, 'properties')
            strategy_properties.attrib['class'] = 'java.util.Arrays$ArrayList'
            prop_a = XML.SubElement(strategy_properties, 'a')
            prop_a.attrib['class'] = 'jenkins.branch.BranchProperty-array'
            XML.SubElement(prop_a, 'jenkins.branch.NoTriggerBranchProperty')
