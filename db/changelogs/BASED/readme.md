This document outlines standards for maintaining BASED database changelogs.

Before planning a database change, ensure that you read and adhere to the Liquibase best practices: https://docs.liquibase.com/concepts/bestpractices.html

# Additional standards

Changeset IDs in this project are formatted as:

> [changeset_index]-[ticket_number]<-[descriptor]>

* `changeset_index` is the index of the changeset within the changelog file. This always starts at 1, and increases in increments of 1.
* `ticket_number` is the BASED GitHub issue which is responsible for the change.
* `descriptor` is optional extra semi-free text for identifying the change.
  The descriptor must be short (less than 50 characters), alphanumeric (plus underscores), and unique within a file and ticket number

Examples:
* `1-81-initial`
* `2-23-new_table`
* `3-23-new_table_2`
* `4-5`