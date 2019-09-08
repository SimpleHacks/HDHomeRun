# hdhr_dvr_scripts

These are some simple python scripts that use the HDHomeRun DVR API

* tasks.py - A list of your DVR tasks, including the Task (Rule) ID and Series ID
* search.py - Search for a series; will return the Series ID
* addseries.py - Add a task for the series ID. Defauts to zero seconds start padding, but you can change that
* deletetask.py - Delete a task (get the Task ID using tasks)
* upcoming.py - List upcoming episodes for a Series ID
* allupcoming.py - List upcoming episodes for all series
* movies.py - List upcoming movies
* discover.py - Find the IP for local tuner

The most complex part of these scripts is the discovery, the entire credit for that goes to Gary Burh: https://github.com/garybuhrmaster/HDHRUtil
