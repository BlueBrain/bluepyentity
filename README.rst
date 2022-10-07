entity-manager
==============

NEXUS Productivity Layer


Installation
------------

.. Replace this text by proper installation instructions.


Examples: Command Line Interaction
----------------------------------


Token:
------

Using the `keyring`_, a NEXUS token can be stored to reduce the number of required authentication steps:

.. code-block:: bash

    token='copy your token here'
    entity-manager token set --token $token

One can see the contents of the token with:

.. code-block:: bash

    entity-manager token decode

One can get the token with (note that this can be piped to other apps that need the token, or saved as an environment variable:

.. code-block:: bash

    entity-manager token get

    # save as environment variable:

    token=`entity-manager token get`

Info:
-----

One can look at the associated information of an identifier with:

.. code-block:: bash

    entity-manager info SOME_ID

.. _`keyring`: https://github.com/jaraco/keyring
