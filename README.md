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
4. Build your bot directly over BASED.

This project is already working as is, with a connected client instance, dynamic commands importing and calling, scheduler and database initialization, and reactionMenu interaction using client events. To test the base project, try running the bot, and calling the `.help` command.

See the `commands` module for examples of adding new commands.
If you add a new commands module, enable it by adding the module name to the `enabledCommandsModules` config variable.

BASED is *not* a library, it is a *template* to be used as a starting point for your project.

# Configuring Your Bot

BASED v0.3 adds the ability to configure all of the bot's cfg attributes externally with toml.
If a bot token is provided by the default config values (found in `cfg/cfg.py`), use of a config file is entirely optional.

- All config variables are optional.
- Generate a default config file with all variables and their defaults, by running `makeDefaultConfig.py`.
  - You can optionally specify the file name (or path to the file name) to generate into, e.g `python makeDefaultConfig.py configs/myBotConfig.py`.
- Any emoji can be either unicode or custom.
  - give custom emojis as the integer emoji ID.
  - give unicode emojis as a string containing a single unicode emoji character.
  
### Providing your bot token

The bot token can now be given in a config variable, or in an environment variable whose name is specified in config:
- specify your token directly, in the `botToken` config var, or
- give the name of the environment variable containing your token, in `botToken_envVarName`

You must give exactly one of these variables, either in the default config values (`cfg/cfg.py`), or in a toml config file.
    

# Running Your Bot
### Option 1: Direct
To run your bot, simply run `main.py`.
To load a config.toml, provide a path to your config in command line args, e.g `python main.py myConfig.toml`.

### Option 2: Shell launch loop
Alternatively, automatic restarting and updating of the bot are provided by using one of the two looping bot launching scripts, `run.bat` and `run.sh`.<br>
Your bot will be rebooted automatically after critical errors, or on use of the `dev_cmd_restart` command.
> The script will not restart your bot on receipt of interrupt and termination signals (`SIGINT`/`SIGTERM`).

If your bot is a git repository, give your run script the `-g` optional argument to enable `dev_cmd_update`.<br>
Running `dev_cmd_update` will shut down the bot, run `git pull`, and restart the bot again.
- If conflicts are encountered with merging commits, the pull will be cancelled entirely.
- This error will not be announced to discord, and you should check your console to ensure that it was successful.
  > (or implement a bot version checking command)


# How to Update Your BASED Fork

When new versions of BASED are released, assuming you have update checking enabled in `cfg.BASED_checkForUpdates`, you will be notified via console.<br>
To update your BASED fork, create a pull request from Trimatix/BASED/master into your fork.<br>
Beware: conflicts are likely in this merge, especially if you have renamed BASED files, classes, functions or variables.
