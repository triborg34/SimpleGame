

import json

import re
s= "age = json['age'] camera = json['camera'] collectionId = json['collectionId']; collectionName = json['collectionName']; croppedFrame = json['cropped_frame']; date = json['date']; frame = json['frame']; gender = json['gender']; id = json['id'];  name = json['name'];  score = json['score']; time = json['time'];  trackId = json['track_id']; role=json['role']; humancrop=json['humancrop']"


matches = re.findall(r"(\w+)\s*=\s*json\['(\w+)'\]", s)

# Step 2: turn into dict
json_dict = { f"{k}:json['{v}']" for k, v in matches}  # placeholder values
# Step 3: make a separate list of just the keys
for k,v in matches :
    print(f"{k}:json.data['{v}'],")
