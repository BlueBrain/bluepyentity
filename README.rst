bluepyentity
============

NEXUS Productivity Layer, helps to:

- access NEXUS through the command line interface
- provide convenience functions to simplify common operations using NEXUS

Installation
------------

From PyPi:

.. code-block:: bash

   pip install bluepyentity


Usage and examples: Command Line Interaction
--------------------------------------------


Token:
~~~~~~

Using the `keyring`_, a NEXUS token can be stored to reduce the number of required authentication steps:

.. code-block:: bash

    token='copy your token here'
    bluepyentity token set --token $token

One can see the contents of the token with:

.. code-block:: bash

    bluepyentity token decode

One can get the token with (note that this can be piped to other apps that need the token, or saved as an environment variable):

.. code-block:: bash

    bluepyentity token get

    # save as environment variable:

    token=`bluepyentity token get`

Info:
~~~~~

One can look at the associated information of an identifier with:

.. code-block:: bash

    bluepyentity info SOME_ID

Explorer:
~~~~~~~~~

One can navigate the links of an identifier with:


.. code-block:: bash

    bluepyentity explorer SOME_ID

.. _`keyring`: https://github.com/jaraco/keyring


Acknowledgements
----------------

The development of this software was supported by funding to the Blue Brain Project, a research center of the École polytechnique fédérale de Lausanne (EPFL), from the Swiss government’s ETH Board of the Swiss Federal Institutes of Technology.

This project/research has received funding from the European Union’s Horizon 2020 Framework Programme for Research and Innovation under the Specific Grant Agreement No. 785907 (Human Brain Project SGA2).

License
-------

Refer to `LICENSE.txt` <https://github.com/BlueBrain/bluepyentity/blob/master/LICENSE.txt>`__


Copyright (c) 2019-2024 Blue Brain Project/EPFL
