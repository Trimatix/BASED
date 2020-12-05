![BASED Banner](https://dl.dropboxusercontent.com/s/chs2lkestx3ap8j/BASED%20cover.png)

BASED is a template project for creating advanced discord bots using python.

BASED includes complete implementations for task scheduling, object and database saving with JSON, per-guild command prefixing, and custom access level-based commands handling with help command auto-generation.

BASED also includes a handy and extraordinarily versatile reaction menu implementation, allowing per-menu type saving implementations, advanced per-option menu behaviour, and support for both 'inline' and 'passive' calling styles.

Much more to come, including a game-specific fork with pre-written item and inventory classes.

# How to Make a BASED App
To make use of BASED, fork this repository and build your bot directly over BASED.
BASED is *not* a library, it is a *template* to be used as a starting point for your project.

Before your bot can be used, you will need to create an environment variable named `BASED_DC_TOKEN`, containing your discord bot's token.

In the future, this variable name will be configurable.

# How to Update Your BASED Fork
When new versions of BASED are released, assuming you have update checking enabled in `cfg.BASED_checkForUpdates`, you will be notified via console.
To update your BASED fork, create a pull request from the master branch of this repository into your fork.
Beware: conflicts are likely in this merge, especially if you have renamed BASED files, classes, functions or variables.

README unfinished.
