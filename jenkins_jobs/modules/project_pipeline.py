# -*- coding: utf-8 -*-
# Copyright (C) 2015 David Caro <david@dcaro.es>
# Copyright (C) 2015 Joost van der Griendt <joostvdg@gmail.com>
#
# Based on jenkins_jobs/modules/project_flow.py by
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
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
    * **script** (`str`): The DSL content.
    * **sandbox** (`bool`): If the script should run in a sandbox (default
      false)
    * **script-path** (`str`): The name and location of the DSL file to
      execute as workflow.



Job with inline script example:

    .. literalinclude::
      /../../tests/yamlparser/fixtures/project_pipeline_template001.yaml

Job with external script example:

    .. literalinclude::
      /../../tests/yamlparser/fixtures/project_pipeline_template004.yaml


Job template example:

    .. literalinclude::
      /../../tests/yamlparser/fixtures/project_pipeline_template002.yaml

"""
import logging
import xml.etree.ElementTree as XML
from jenkins_jobs.errors import (JenkinsJobsException)
import jenkins_jobs.modules.base
import jenkins_jobs.modules.parameters


class Pipeline(jenkins_jobs.modules.base.Base):
    sequence = 0

    def root_xml(self, data):
        xml_parent = XML.Element('flow-definition')
        xml_parent.attrib['plugin'] = 'workflow-job'

        definition = XML.SubElement(xml_parent, 'definition')
        definition.attrib['class'] = 'org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition'
        definition.attrib['plugin'] = 'workflow-cps'

        if 'pipeline' not in data:
            return xml_parent

        pipeline = data['pipeline']

        if 'properties' in pipeline:
            Parameters.gen_xml(self, definition, data)

        if 'scm' in pipeline and 'git' in pipeline['scm']:
            self.git(definition, pipeline['scm']['git'])
            definition.attrib['class'] = 'org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition'

        if 'script' in pipeline:
            XML.SubElement(definition, 'script').text = pipeline.get('script', '')
            needs_workspace = pipeline.get('sandbox', True)
            XML.SubElement(definition, 'sandbox').text = str(needs_workspace).lower()

        if 'script-path' in pipeline:
            XML.SubElement(definition, 'scriptPath').text = pipeline.get('script-path', '')

        return xml_parent

    def git(self, xml_parent, data):
        logger = logging.getLogger("%s:pipeline-git" % __name__)
        scm = XML.SubElement(xml_parent,
                             'scm', {'class': 'hudson.plugins.git.GitSCM'})
        scm.attrib['plugin'] = 'git'
        XML.SubElement(scm, 'configVersion').text = '2'

        user = XML.SubElement(scm, 'userRemoteConfigs')

        if 'remotes' not in data:
            data['remotes'] = [{data.get('name', 'origin'): data.copy()}]

        for remoteData in data['remotes']:
            huser = XML.SubElement(user, 'hudson.plugins.git.UserRemoteConfig')
            remoteName = next(iter(remoteData.keys()))
            #XML.SubElement(huser, 'name').text = remoteName
            remoteParams = next(iter(remoteData.values()))

            if 'url' in remoteParams:
                remoteURL = remoteParams['url']
            else:
                raise JenkinsJobsException('Must specify a url for git remote \"' +
                                           remoteName + '"')
            XML.SubElement(huser, 'url').text = remoteURL
            if 'credentials-id' in remoteParams:
                credentialsId = remoteParams['credentials-id']
                XML.SubElement(huser, 'credentialsId').text = credentialsId

        xml_branches = XML.SubElement(scm, 'branches')
        branches = data.get('branches', ['**'])

        for branch in branches:
            bspec = XML.SubElement(xml_branches, 'hudson.plugins.git.BranchSpec')
            XML.SubElement(bspec, 'name').text = branch

        # add addition elements
        #<doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
        #<submoduleCfg class="list"/>

        mappingOld = [
        # option, xml name, default value (text), attributes (hard coded)
            (None, 'doGenerateSubmoduleConfigurations', False),
            (None, 'submoduleCfg', '', {'class': 'list'}),
        ]

        mapping = [
            # option, xml name, default value (text), attributes (hard coded)
            ("ignore-notify", "ignoreNotifyCommit", False),
            ("shallow-clone", "useShallowClone", False),
        ]

        # first adding the deprecated options
        for elem in mappingOld:
            (optname, xmlname, val) = elem[:3]
            attrs = {}
            attrs = {}
            if len(elem) >= 4:
                attrs = elem[3]
            xe = XML.SubElement(scm, xmlname, attrs)
            if optname and optname in data:
                val = data[optname]
            if type(val) == bool:
                xe.text = str(val).lower()
            else:
                xe.text = val

        exts_node = XML.SubElement(scm, 'extensions')
        for elem in mapping:
            (optname, xmlname, val) = elem[:3]
            attrs = {}
            if len(elem) >= 4:
                attrs = elem[3]
            xe = XML.SubElement(exts_node, xmlname, attrs)
            if optname and optname in data:
                val = data[optname]
            if type(val) == bool:
                xe.text = str(val).lower()
            else:
                xe.text = val
