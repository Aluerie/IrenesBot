⚙️ Setup Guide
==============

.. warning::
    I would probably prefer if you don't run an instance of my bot. And I'm honestly not a very good programmer. Nevertheless:

🤵 Requirements
###############

* Python ``3.14`` or higher;
* SQL database, preferably ``PostgreSQL``.
* A bunch of various API tokens for ``.env`` file.

🔨 Installation
###############

1. Clone the :iconify:`fa-brands:github` `repository <https://github.com/Aluerie/IrenesBot>`_ and change directory to the newly created folder:

   .. code-block:: bash
      
      git clone https://github.com/Aluerie/IrenesBot
      cd ./IrenesBot

2. Set up a virtual environment (venv) with your preferred :iconify:`devicon:python` Python package manager. I prefer :iconify:`material-icon-theme:uv` `uv <https://docs.astral.sh/uv/>`_. 
   This repository is fully setup with its help which means if you use it - it will automatically solve some chores for you even when running ``uv run src/main.py``. 
   But feel free to use any other :iconify:`devicon:python` Python package manager (``py``, ``pdm``, ...)
   I also made a :iconify:`material-icon-theme:makefile` Makefile (it uses :iconify:`devicon:powershell` powershell profile by default) with some handy instructions for some common operations.
   I recommend using them.

   .. tab-set::
      :class: outline

      .. tab-item:: :iconify:`material-icon-theme:makefile` Makefile

         .. code-block:: bash

            make setup

      .. tab-item:: :iconify:`:material-icon-theme:uv` uv

         .. code-block:: bash

            uv sync

      .. tab-item:: :iconify:`devicon:pypi` pip

         .. code-block:: bash

            python3.14 -m venv venv # or
            py -m venv venv # or your favorite package manager way

3. This repository uses a git submodule :iconify:`fa-brands:github` `shared <https://github.com/Aluerie/Shared-Bot-Utilities>`_. We need to update it after initial cloning. 
   ``make setup`` automatically does it (so you can skip to the next step if you used it), but if not then please do:

   .. code-block:: bash

      git submodule update --init --recursive

4. Activate the venv with

   .. code-block:: bash

      ./venv/Scripts/Activate.ps1 # Powershell Windows
      source ./venv/bin/activate # Ubuntu
      # Etc

5. Install dependencies with

   .. tab-set::
      :class: outline

      .. tab-item:: :iconify:`material-icon-theme:makefile` Makefile

         .. code-block:: bash

            make sync

      .. tab-item:: :iconify:`:material-icon-theme:uv` uv

         .. code-block:: bash

            uv sync  # Yes, I'm repeating myself, oups.

      .. tab-item:: :iconify:`devicon:pypi` pip

         .. code-block:: bash

            python3.14 -m pip install . # or
            py -m pip install . # or your favorite package manager way

6. Rename-copy ``.env.example`` to ``.env`` and fill out all the needed config parameters, api-keys, credentials and passwords in it.
7. Replace twitch ID and some other constant variables in files under ``/utils/const`` folder with your own.
8. Create :iconify:`griddy-icons:sql` SQL tables using definitions from ``.sql``-files in ``sql`` folder.
9. Run the bot with one of the following commands.
   Note that I chose to have working directory as project root folder and run the bot with ``uv run src/main.py`` over switching directory to ``src`` first.
   I also have a bunch of CLI arguments for ``src/main.py`` script that you can check with ``uv run src/main.py --help`` or inspecting the file itself.

   .. tab-set::
      :class: outline

      .. tab-item:: :iconify:`material-icon-theme:makefile` Makefile

         .. code-block:: bash

            make run

      .. tab-item:: :iconify:`:material-icon-theme:uv` uv

         .. code-block:: bash

            uv run src/main.py  # can add some CLI arguments

      .. tab-item:: :iconify:`devicon:python` python

         .. code-block:: bash

            python src/main.py  # can add some CLI arguments

🌊 Process Managers
###################

Personally, I use ``systemd`` for process managing. 
You can use anything you like though: :iconify:`devicon:docker` dockers, simple manual :iconify:`devicon:python` python ``python src/main.py``, etc. 
An example of my ``.service`` file is in the repository root folder.

.. tip::
   A good template for ``.service`` files can be found in `gist by @mikeshardmind <https://gist.github.com/mikeshardmind/4c88f17cc607e30be57a27a840fde617>`_. 
   The options are explained pretty well at `freedesktop.org <https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html>`_.

🔌 Adapter Setup
#################

1. Decide whether you want to use local adapter (**localhost**) or remote (personally, I'm currently using **ngrok-free.app**).
   Remote allows other people to authorize the bot permissions, but requires a web app with a public-facing URL running.
   While localhost is perfect for one-channel bots, nothing wrong with a bot serving only one channel.

   .. caution::

      In the further points I will use ``https://parrot-thankful-trivially.ngrok-free.app`` as an example for *my own convenience* - 
      replace it with your own public-facing URL if you are actually making a twitch bot of your own. 

2. `Twitch Developer Console <https://dev.twitch.tv/console>`_ with the bot application (e.g. for me at ``@Irene_Adler__`` account).
   We need to edit **OAuths Redirect URLs**:
   
   .. tab-set::

      .. tab-item:: Local

         http://localhost:4343/oauth/callback

      .. tab-item:: Ngrok

         https://parrot-thankful-trivially.ngrok-free.app/oauth/callback

   .. image:: /_static/images/twitch-dev-console.png

3. At this point, with ``local`` setup - no extra actions needed, skip to the next step.
   Ngrok, however, needs a setup:
   In your terminal run (``parrot-thankful-trivially.ngrok-free.app`` is host-name I was given so replace that with your own):

   .. code-block:: bash

      ngrok http --url=parrot-thankful-trivially.ngrok-free.app 4343

   Note that the port should be 4343, as twitchio adapter works on it as well.
   Ignore ngrok dashboard saying to use port 80, it's just an example.

   .. tip:: 

      You can setup ``ngrok service`` for the web-app server to run 24/7. 
      I have examples of ``ngrok.yml`` config file in the root folder.
      After creating ngrok config file you can create and manage ngrok service with various commands:

      .. code-block:: bash

         ngrok service install --config .config/ngrok/ngrok.yml
         ngrok service start / stop / restart / run / install / uninstall

4. Simply run the bot with a proper ``--adapter=`` CLI option (``local`` or ``remote``).
   
   .. code-block:: bash

      uv run src/main.py --adapter=local

   Now users should be able to visit a link like this

   .. tab-set::

      .. tab-item:: Local

         http://localhost:4343/oauth?scopes=channel:bot&force_verify=true

      .. tab-item:: Ngrok

         https://parrot-thankful-trivially.ngrok-free.app/oauth?scopes=channel:bot&force_verify=true

   and be able to authorize the bot.
   Note, to get a proper link with ALL proper scopes - launch the bot in `-s` (`--scopes-only`) mode. 
   Or use the link provided in the :ref:`how_to_invite` section.

✅ Troubleshooting
##################

*  If something goes wrong with conduits or permissions - it's likely that running the bot with ``uv run src/main.py --force-subscribe`` will solve the issue.
   The conduits stay alive only for 72 hours. 
   They also don't automatically refresh when adding new permissions (unless I fixed that in the ``core.bot`` module?).
