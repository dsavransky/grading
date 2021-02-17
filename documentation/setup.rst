.. _Setup:

Setup
==============

cornellGrading setup involves two steps:

#. Installation
#. API Token setup

Both steps must be completed prior to using the code.

Installation
---------------------------

From PyPI (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^

To install from PyPI: ::

    pip install --user cornellGrading

Or, with optional dependencies required to push LaTeX into Canvas HTML: ::

    pip install --user cornellGrading[latex2html]

To install system-wide, omit the ``--user`` option. This requires administrative privileges on most systems.

.. note::

    The ``latex2html`` option requires the pandoc executable to be installed and in the system PATH.  For detailed pandoc installation instructions see here: https://pandoc.org/installing.html

From GitHub
^^^^^^^^^^^^^^^^^

If cloning from github, in the cloned grading directory: ::


    pip install --user .

or, to install in developer mode: ::


    pip install --user -e .

In order to also install requirements needed push LaTeX into Canvas HTML, do: ::


    pip install --user -e .[latex2html]

.. note::

    To upgrade to the latest version, just append ``--upgrade`` to whichever install command you originally used.  For example: ``pip install --upgrade --user cornellGrading``.


Canvas API Token (Required)
-----------------------------
To generate a token, in Canvas: 

#. Navigate to Account>Settings and scroll down to Approved Integrations
#. Click '+New Access Token'.  Copy the token.  **NB: It won't be displayed again.**

You will need to enter this token the first time you instantiate a :py:class:`cornellGrading.cornellGrading` object. If using Windows, you should save this token to a text file. Be sure that there is nothing other than the token in the file (white space afterwards is ok).

.. warning::

    Windows users working with a standard shell will be unable to copy/paste this token into the command prompt.  Windows users should use the ``canvas_token_file`` input when instantiating :py:class:`~cornellGrading.cornellGrading` for the first time, or retype it into the prompt.  Using a text file is recommended. 

.. note::

   The token is stored in your system's keychain as ``canvas_test_token1`` and will be automatically loaded on all subsequent :py:class:`cornellGrading.cornellGrading` instantiations.  If you need to change the local token, you must manually delete it from the keychain. The token is entered as a secure password, and so you will not see the cursor move as you enter it. The token will only be saved if the connection to Canvas is successful.

In order to load the token into your system's keychain, in python:

.. code-block:: python
    
    from cornellGrading import cornellGrading
    c = cornellGrading(canvas_token_file=r'path_to_token_file') #replace with fullpath to the text file with your token
 
You can also omit the ``canvas_token_file`` input, in which case you will be prompted to enter your token at the command line.

.. note::

    If entering your token at the prompt, you will not see the cursor move.  Just hit Enter when done.  Windows users must type the token out.  Others can copy/paste.

Qualtrics API Token (Optional)
--------------------------------
On the qualtrics site:

#. Navigate to: Account Settings>Qualtrics IDs
#. Click the 'Generate Token' button under API
#. This page also lists all other IDs you need to know

You will need to enter this token the first time you run :py:meth:`~.cornellGrading.setupQualtrics`.   If using Windows, you should save this token to a text file. Be sure that there is nothing other than the token in the file (white space afterwards is ok).

.. warning::

    Windows users working with a standard shell will be unable to copy/paste this token into the command prompt.  Windows users should use the ``qualtrics_token_file`` input when running :py:meth:`~.cornellGrading.setupQualtrics` for the first time, or just retype it into the prompt. Using a text file is recommended. 


.. note::

   The token is stored in your system's keychain as ``qualtrics_token`` and will be automatically loaded on all subsequent :py:meth:`~.cornellGrading.setupQualtrics` calls.  If you need to change the local token, you must manually delete it from the keychain. The token is entered as a secure password, and so you will not see the cursor move as you enter it. The token will only be saved if the connection to Canvas is successful.


In order to load the token into your system's keychain, in python:

.. code-block:: python
    
    from cornellGrading import cornellQualtrics
    c = cornellQualtrics(qualtrics_token_file=r'path_to_token_file') #replace with fullpath to the text file with your token
 
You can also omit the ``qualtrics_token_file`` input, in which case you will be prompted to enter your token at the command line.

.. note::

    If entering your token at the prompt, you will not see the cursor move.  Just hit Enter when done.  Windows users must type the token out.  Others can copy/paste.


Qualtrics De-Anonymization
-----------------------------
By default, Cornell anonymizes all survey responses, regardless of how you have set up your survey.  To fix this, email itservicedesk@cornell.edu and request that they toggle  "View Restricted Data" to On for your qualtrics account.

