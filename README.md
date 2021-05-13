# propro_forwarder

## Current function
** tweet and youtube forward**
1. create a database to store the information of vtuber's tweets and there youtube videos
2. update database by ytTracker.py and twitterTracker.py, call by systemd(linux)
3. use these data and forward data in json to forward twitter and youtube to target discord channel
** update upcoming, live video in select channel **
1. load data from database which is waiting vtuber start their stream and update select message
2. load data from database which is streaming and update select message
3. can press assigned reaction to update by hand


## To-do
1. 新增yt資料來源: RSS
2. 檢查yt quota使用量
3. 新增yt api指令方便快速查詢
4. 可能需要新增sql指令
### 功能
* 自動產生notion行事曆
* 想辦法讓錯誤發生時可以自動重啟並記錄，至少要能顯示出來
* 手動embed
* 研究web template
* 改寫為可跨伺服使用之bot

