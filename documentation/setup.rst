Setup
==============

Installation
---------------------------
To install from PyPI: ::

    pip install --user cornellGrading

Or, with optional dependencies required to push LaTeX into Canvas HTML: ::

    
    pip install --user cornellGrading[latex2html]

To install system-wide, omit the ``--user`` option.

.. note::

    The ``latex2html`` option requires the pandoc executable to be installed and in the system PATH.  For detailed pandoc installation instructions see here: https://pandoc.org/installing.html

If cloning from github, in the cloned grading directory: ::


    pip install --user .

or, to install in developer mode: ::


    pip install --user -e .

In order to also install requirements needed push LaTeX into Canvas HTML, do: ::


    pip install --user -e .[latex2html]


Canvas API Token
-------------------
To generate token, in Canvas: 

#. Navigate to Account>Settings and scroll down to Approved Integrations
#. Click '+New Access Token'.  Copy the token.  **NB: It won't be displayed again.**

You will need to enter this token the first time you instantiate a :py:class:`cornellGrading.cornellGrading` object. If using Windows, you should save this token to a text file. Be sure that there is nothing other than the token in the file (white space afterwards is ok).

.. note::

   The token is stored in your system's keychain as ``canvas_test_token1`` and will be automatically loaded on all subsequent :py:class:`cornellGrading.cornellGrading` instantiations.  If you need to change the local token, you must manually delete it from the keychain. The token is entered as a secure password, and so you will not see the cursor move as you enter it. The token will only be saved if the connection to Canvas is successful.

.. warning::

    Windows users working with a standard shell will likely be unable to copy/paste this token into the command prompt.  Windows users should use the ``canvas_token_file`` input when instantiating :py:class:`~cornellGrading.cornellGrading` for the first time, or just retype it into the prompt.



Qualtrics API Token
-------------------------
On the qualtrics site:

#. Navigate to: Account Settings>Qualtrics IDs
#. Click the 'Generate Token' button under API
#. This page also lists all other IDs you need to know

You will need to enter this token the first time you run :py:func:`~cornellGrading.cornellGrading.setupQualtrics`

.. note::

   The token is stored in your system's keychain as ``qualtrics_token`` and will be automatically loaded on all subsequent :py:meth:`cornellGrading.cornellGrading.setupQualtrics` calls.  If you need to change the local token, you must manually delete it from the keychain. The token is entered as a secure password, and so you will not see the cursor move as you enter it. The token will only be saved if the connection to Canvas is successful.

.. warning::

    Windows users working with a standard shell will likely `be unable to copy/paste this token into the command prompt.  Windows users should use the ``qualtrics_token_file` input when running :py:func:`~cornellGrading.cornellGrading.setupQualtrics` for the first time, or just retype it into the prompt.


Qualtrics De-Anonymization
-----------------------------
By default, Cornell anonymizes all survey responses, regardless of how you have set up your survey.  To fix this, email itservicedesk@cornell.edu and request that they toggle  "View Restricted Data" to On for your qualtrics account.

