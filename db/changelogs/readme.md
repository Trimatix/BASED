This project uses Liquibase for database change management.

BASED sets out its own standards for maintaining changelogs, found in the BASED folder.
You may or may not choose to follow similar standards for your project.

To get started, create a folder for your project, with your changelog inside:

```
- db/changelogs
  - BASED
  - my_project
    - my_changelog.yaml
```

and include the BASED root changelog in your changelog:

*my_changelog.yaml*
```yaml
databaseChangeLog:
  - include:
      file: ../BASED/db.changelog-root.yaml
```