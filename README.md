# hdhr_dvr_scripts

These are some simple python scripts that use the HDHomeRun DVR API

* tasks - A list of your DVR tasks, including the Task (Rule) ID and Series ID
* search - Search for a series; will return the Series ID
* addseries - Add a task for the series ID. Defauts to zero seconds start padding, but you can change that
* deletetask - Delete a task (get the Task ID using tasks)
* upcoming - List upcoming episodes for a Series ID
* allupcoming - List upcoming episodes for all series
