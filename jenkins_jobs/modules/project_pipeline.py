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
You may specify ``pipeline`` in the ``project-type`` attribute of
the :ref:`Job` definition.

You can add an SCM with the script-path, but for now only GIT is supported.

Requires the Jenkins :jenkins-wiki:`Pipeline Plugin <Pipeline+Plugin>`.

In order to use it for job-template you have to escape the curly braces by
doubling them in the script: { -> {{ , otherwise it will be interpreted by the
python str.format() command.

You can also include the inline script via a file.
With the include mechanism.
e.g. !include-raw-escape: include/pipeline-inline-script.txt

Either you use a inline script, or you use a scm with a script path.
Currently only git is supported as SCM.
See the git plugin in the scm section for how to use it.

When using from scm, you are automatically in sandbox mode.
So the sandbox param is only evaluated if you do an inline script.

:arg dict pipeline:
    * **script** (`str`): The DSL content.
    * **sandbox** (`bool`): If the script should run in a sandbox (default
      true)
    * **script-path** (`str`): The name and location of the DSL file to
      execute as workflow.
    * **scm** (`dict`): The SCM section
    * **properties** (`dict`): the properties section, see Parameters

Job with inline script example:
    .. literalinclude::
        /../../tests/yamlparser/fixtures/project_pipeline_template001.yaml

Job with external script example:
    .. literalinclude::
        /../../tests/yamlparser/fixtures/project_pipeline_template004.yaml

"""
import logging
import xml.etree.ElementTree as XML
from jenkins_jobs.errors import (JenkinsJobsException)
import jenkins_jobs.modules.base
import jenkins_jobs.modules.parameters

from scm import git


class Pipeline(jenkins_jobs.modules.base.Base):
    """
        Project type for the Jenkins Pipeline plugin.
    """

    sequence = 0

    def root_xml(self, data):
        """
            Defines the xml for the project.
        """
        logger = logging.getLogger("%s:pipeline" % __name__)

        xml_parent = XML.Element('flow-definition')
        xml_parent.attrib['plugin'] = 'workflow-job'
        definition = XML.SubElement(xml_parent, 'definition')
        definition.attrib['class'] = 'org.jenkinsci.plugins.workflow.cps.\
         CpsFlowDefinition'
        definition.attrib['plugin'] = 'workflow-cps'

        if 'pipeline' not in data:
            logger.warn('No pipeline information')
            return xml_parent

        pipeline = data['pipeline']

        if 'properties' in pipeline:
            Parameters.gen_xml(self, definition, data)

        if 'scm' in pipeline and 'git' in pipeline['scm']:
            git(self, definition, pipeline['scm']['git'])
            definition.attrib['class'] = 'org.jenkinsci.plugins.workflow.cps. \
             CpsScmFlowDefinition'

        if 'script' in pipeline:
            XML.SubElement(definition, 'script').text = pipeline.get(
                'script', '')
            needs_workspace = pipeline.get('sandbox', True)
            XML.SubElement(definition, 'sandbox').text = str(
                needs_workspace).lower()

        if 'script-path' in pipeline:
            XML.SubElement(definition, 'scriptPath').text = pipeline.get(
                'script-path', '')

        return xml_parent
