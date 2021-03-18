ALLOWED_PROFILE_IMAGE_FORMATS = ['image/png', 'image/jpg', 'image/jpeg']

# 10 mb, written in bytes
MAX_PROFILE_IMAGE_SIZE = 10485760 

# 3 mb, written in bytes
MAX_STATUS_FILE_SIZE = 3145728

# max number of file uploads allowed for a status
MAX_STATUS_FILES = 5

# Node server base url (domain)
NODE_SERVER_DOMAIN = 'https://chats.bditto.com/'
DJANGO_SERVER_DOMAIN = 'https://api.bditto.com'
EMAIL_DOMAIN="https://bditto.com"      
# Node server admin token
NODE_ADMIN_TOKEN = '9846898379530075B66CB96DDAE9324363F4A7E28B15721A39BA9342742FA6AB'

DJANGO_ADMIN_TOKEN  = 'fM8KjhPa1QnsSUFqHaX3CTSSvsFkDLDA'


STATUS_MATCH_THRESHOLD = 0.4

class Constants:
    # User access 
    USER_STATUS = (
        ('Activated','Activated'),
        ('Deactivated','Deactivated'),
        ('Blocked','Blocked'),
        ('Deleted','Deleted')
    )

    # User gender
    GENDER = (
        ('Male','Male'),
        ('Female','Female'),
        ('Other','Other')
    )

    # status of Issues related to the application
    REPORT_ISSUE_STATUS = (
        ('pending','pending'),
        ('resolved','resolved'),
        ('discarded','discarded')
    )

    # status of status.
    CURRENT_STATUS = (
        ('active','active'),
        ('inactive','inactive'),
        ('deleted','deleted')
    )

    # Friend Request status
    REQUEST_STATUS = (
        ('pending','pending'),
        ('accepted','accepted'),
        ('blocked','blocked')
    )

    # Report user status
    REPORT_STATUS = (
        ('pending','pending'),
        ('resolved','resolved'),
        ('discarded','discarded')
    )

    NOTIFICATION_TYPE = (
        ('friend_request_accepted','Friend Request Accepted'),
        ('friend_request_sent','Friend Request Sent'),
        ('message','Message'),
        ('like','Status Liked'),
        ('group_joined','Group Joined'),
        ('liked_message','Message Liked'),
    )

STOP_WORDS = ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", 
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her',
    'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 
    'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was',
    'were', 'be', 'been', 'being', 'have', 'has', 'had','having', 'do', 'does', 'did', 'doing', 'a', 'an',
    'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 
    'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to',
    'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 
    'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 
    'other', 'some', 'such', 'no', 'nor', 'not', 'only',"you'll", "you'd",
    'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should'
    , "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 
    'didn', "didn't", 'doesn', "doesn't", 'hadn',  'wouldn',"won't",
    "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't",
    'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', 
    "wouldn't", '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', ';', '<', '=',
     '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~', '']