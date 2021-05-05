import os, json

#import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

api_service_name = "youtube"
api_version = "v3"

with open('yt_api.json','r', encoding='utf8') as f:
    yt_api_setting = json.load(f)
    f.close()
DEVELOPER_KEY = yt_api_setting["DEVELOPER_KEY"]
youtube = googleapiclient.discovery.build(
    api_service_name, api_version, developerKey = DEVELOPER_KEY)

def Videos(id, part=None):
    if (part==None):
        part="snippet,statistics,liveStreamingDetails"
        
    request = youtube.videos().list(part=part,id=id)
    response = request.execute()

    return(response)
def SearchList( part="snippet", 
                channelId="",
                eventType="upcoming",
                q="プロプロ"):
    request = youtube.search().list(
        part=part,
        channelId="",
        eventType=eventType,
        maxResults=20,
        q=q,
        type="video"
    )
    response = request.execute()    
    return response
if __name__ == "__main__":
    print(json.dumps(Videos(id="2CUApwfPwl0"), ensure_ascii=False, indent=4))