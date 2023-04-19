<p align="center">
  <img
    src="https://i.imgur.com/7SMgF0t.png"
    alt="BASED Logo"
  />
</p>
<h1 align="center">Bot Advanced Schematic - Easy Discord! (BASED)</h1>
<p align="center">
  <a href="https://github.com/Trimatix/BASED/actions"
    ><img
      src="https://img.shields.io/github/workflow/status/Trimatix/BASED/BASED"
      alt="GitHub Actions workflow status"
  /></a>
  <a href="https://github.com/Trimatix/BASED/labels/bug"
    ><img
      src="https://img.shields.io/github/issues-search?color=eb4034&label=bugs&query=repo%3ATrimatix%2FBASED%20is%3Aopen%20label%3Abug"
      alt="GitHub open bug reports"
  /></a>
</p>
<p align="center">
  <a href="https://sonarcloud.io/dashboard?id=Trimatix_BASED"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=Trimatix_BASED&metric=bugs"
      alt="SonarCloud bugs analysis"
  /></a>
  <a href="https://sonarcloud.io/dashboard?id=Trimatix_BASED"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=Trimatix_BASED&metric=code_smells"
      alt="SonarCloud code smells analysis"
  /></a>
  <a href="https://sonarcloud.io/dashboard?id=Trimatix_BASED"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=Trimatix_BASED&metric=alert_status"
      alt="SonarCloud quality gate status"
  /></a>
</p>

BASED is a template project for creating advanced discord bots using python.

<hr>

### Standout Features

- Task scheduler with auto-rescheduling
- Object and database saving with JSON
- Per-guild command prefixing
- Custom access level-based commands handler
  - Help command auto-generation with paged reaction menus
- Highly versatile reaction menu implementation in two calling styles:
  - 'Inline' - yields the calling thread until the results of the menu are available
  - 'Passive' - schedules the menu behaviour while allowing execution to continue immediately

# How to Make a BASED App

1. Fork this repository.
2. Install the project requirements with `pip install -r requirements.txt`.
3. Provide your bot token (see the [Configuring Your Bot](https://github.com/Trimatix/BASED#configuring-your-bot) section below).
4. Create a PostgreSQL database and create a liquibase.properties file (see [Configuring Your Bot](https://github.com/Trimatix/BASED#configuring-your-bot)).
5. Build your bot directly over BASED.

The project is already working as is, with a connected client instance, dynamic commands importing and calling, scheduler and database initialization, and reactionMenu interaction using client events.<br>
To test the base project, try running the bot, and calling the `.help` command.

See the `commands` module for examples of adding new commands.<br>
If you add a new commands module, enable it by adding the module name to the `enabledCommandsModules` config variable.

BASED is *not* a library, it is a *template* to be used as a starting point for your project.

# Configuring Your Bot

As of v2.0, BASED now uses [Carica](https://pypi.org/project/carica/) for configuration by default. This allows your bot to be configured with convenient, auto-generated toml configuration files, while receiving the configuration in code as strongly typed python objects.

Any config variables added to the module as part of your application will automatically be read into the module from toml. For more information, including how to store and receive custom classes in config, see the [Carica repository](https://github.com/Trimatix/Carica).

There is only one required config variable: Your bot's token. You can eliminate the need for a config file entirely by providing your bot token as a default config value (found in `cfg/cfg.py`).

- All config variables are optional.
- Generate a default config file with all variables and their defaults, by running `makeDefaultConfig.py`.
  - You can optionally specify the file name (or path to the file name) to generate into, e.g `python makeDefaultConfig.py configs/myBotConfig.py`.
- Any emoji can be either unicode or custom.
  - Give custom emojis as the integer emoji ID.
  - Give unicode emojis as a string containing a single unicode emoji character.

### Providing your bot token

The bot token can now be given in a config variable, or in an environment variable whose name is specified in config:
- Specify your token directly, in the `botToken` config var, or
- Give the name of the environment variable containing your token, in `botToken_envVarName`

You must give exactly one of these variables, either in the default config values (`cfg/cfg.py`), or in a toml config file.

## Connecting to your database

BASED v2.0 now uses PostgreSQL for savedata management instead of json flatfiles. BASED uses Liquibase for database change management.

Hese is a step-by-step setup guide for your bot's database:

1. Set up a new PostgreSQL database: https://www.postgresql.org/download/
2. Install Liquibase: https://www.liquibase.com/download
3. Download the jar files that Liquibase needs, and place them somewhere accessible - select the most recent version, and then click "jar".
   *If your classes are located within the repository, don't forget to exclude their directory from git.*
   1. https://mvnrepository.com/artifact/org.yaml/snakeyaml/2.0
   ~~2. PostgreSQL driver~~ *removed - this is included with Liquibase*
4. Create a root changelog file in `db/changelogs/<your project name>` for your database schemas.
   Reference the BASED root changelog in this file, as described in `db/changelogs/readme.md`.
5. Make a copy of `_liquibase.properties.template`, and call it `liquibase.properties`
   1. Customize this file with the correct connection details for your database, and your root changelog file.
      For more information on this file, see the Liquibase website: [[Liquibase: search path](https://docs.liquibase.com/concepts/changelogs/how-liquibase-finds-files.html)] [[Liquibase: liquibase.properties](https://docs.liquibase.com/concepts/connections/creating-config-properties.html?Highlight=liquibase.properties)]
   2. If you have not created a root changelog file at this stage, reference the BASED root changelog file.
6. Run `liquibase update` from the commandline to deploy the database schema to your database.
7. Configure your bot to connect to the database, by setting the `databaseConnection` toml config variable.

# Running Your Bot

To run your bot, simply run `main.py`.<br>
To load a config.toml, provide a path to your config in command line args, e.g `python main.py myConfig.toml`.
> This path can be either absolute, or relative to the project root directory


# How to Update Your BASED Fork

When new versions of BASED are released, assuming you have update checking enabled in `cfg.BASED_checkForUpdates`, you will be notified via console.<br>
To update your BASED fork, create a pull request from Trimatix/BASED/master into your fork.<br>
Beware: conflicts are likely in this merge, especially if you have renamed BASED files, classes, functions or variables.

<p align="center">
  *Update: GitHub now provides an easy shortcut for this:
</p>
<p align="center">
  <img
    src="https://i.imgur.com/Tt5JFsT.jpg"
    alt="Simply click the 'Fetch Upstream' button on your repo."
    width=800
  />
</p>
