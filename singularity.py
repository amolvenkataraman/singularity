# SINGULARITY
# A script to automate downloading the content, announcements, and more information from Google Classroom or D2L Brightspace to a local directory in standardized file formats.
# (C) 2023 Amol Venkataraman. Released under the MIT license.
# Version 1.0.0

# Import modules
import os
import sys
import json
import time
import requests
import argparse
from bs4 import BeautifulSoup
from sty import fg, bg, ef, rs
from pytube import YouTube
from tabulate import tabulate
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


# Functions to print with colors and effects
def print_info(*args): print(fg.blue, end=""); print(*args, end=""); print(fg.rs)
def print_succ(*args): print(fg.green, end=""); print(u'\u2713 ', end=""); print(*args, end=""); print(fg.rs)
def print_warn(*args): print(fg.yellow, end=""); print(u'\u26a0 ', end=""); print(*args, end=""); print(fg.rs)
def print_err(*args): print(fg.red, end=""); print(u'\u274c ', end=""); print(*args, end=""); print(fg.rs)
def print_em(*args): print(ef.bold + fg.cyan, end=""); print(*args, end=""); print(rs.bold_dim + fg.rs)


# Argument parsing
parser = argparse.ArgumentParser(description='Download Brightspace classrooms or Google Classrooms.')
# Different download sources
parser.add_argument("-bs", "--brightspace", help="Download a Brightspace course", required=False, action="store_true")
parser.add_argument("-bsa", "--brightspaceall", help="Download ALL Brightspace courses", required=False, action="store_true")
parser.add_argument("-lb", "--listbrightspace", help="List all Brightspace courses", required=False, action="store_true")
parser.add_argument("-gc", "--classroom", help="Download a Google Classroom course", required=False, action="store_true")
parser.add_argument("-gca", "--classroomall", help="Download ALL Google Classroom courses", required=False, action="store_true")
parser.add_argument("-lc", "--listclassroom", help="List All Google Classroom courses", required=False, action="store_true")

parser.add_argument("-i", "--interactive", help="Open an interactive prompt asking the user what to do", required=False, action="store_true")

# Arguments for brightspace
parser.add_argument('-c', '--course', help='Brightspace Course ID', required=False)
parser.add_argument('-ssv', '--securesession', help='Brightspace\'s secure session value cookie', required=False)
parser.add_argument('-sv', '--session', help='Brightspace\'s session value cookie', required=False)
parser.add_argument('-cf', '--cookies', help='JSON list of cookies exported from Brightspace', required=False)
parser.add_argument('-bu', '--baseurl', help='Brightspace base URL', required=False)
parser.add_argument('-gg', '--google', help='Sign in to Google (private Drive files will download)', required=False, action="store_true")
parser.add_argument('-nv', '--novideo', help='Do not download videos from Brightspace', required=False, action="store_true")

# Arguments for google classroom
parser.add_argument('-cid', '--classid', help='Google Classroom class ID', required=False)

# Common arguments
parser.add_argument('-f', '--force', help='Force download all files', required=False, action="store_true")

# Parse arguments
args = parser.parse_args()

SPLASH_TEXT = [
    "  _____ _____ _   _  _____ _    _ _               _____  _____ _________     __",
    " / ____|_   _| \ | |/ ____| |  | | |        /\   |  __ \|_   _|__   __\ \   / /",
    "| (___   | | |  \| | |  __| |  | | |       /  \  | |__) | | |    | |   \ \_/ / ",
    " \___ \  | | | . ` | | |_ | |  | | |      / /\ \ |  _  /  | |    | |    \   /  ",
    " ____) |_| |_| |\  | |__| | |__| | |____ / ____ \| | \ \ _| |_   | |     | |   ",
    "|_____/|_____|_| \_|\_____|\____/|______/_/    \_\_|  \_\_____|  |_|     |_|   ",
]

SCOPES = [
    'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.appdata', 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata',
    'https://www.googleapis.com/auth/classroom.announcements', 'https://www.googleapis.com/auth/classroom.announcements.readonly', 'https://www.googleapis.com/auth/classroom.courses', 'https://www.googleapis.com/auth/classroom.courses.readonly', 'https://www.googleapis.com/auth/classroom.profile.emails', 'https://www.googleapis.com/auth/classroom.profile.photos', 'https://www.googleapis.com/auth/classroom.rosters', 'https://www.googleapis.com/auth/classroom.rosters.readonly',
    'https://www.googleapis.com/auth/classroom.courseworkmaterials', 'https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly', 'https://www.googleapis.com/auth/classroom.topics', 'https://www.googleapis.com/auth/classroom.topics.readonly', 'https://www.googleapis.com/auth/classroom.coursework.me',
]

# Chanacters that can't be used in filenames
BANNED_CHARS = ['<', '>', ':', '"', '/', '\\', '|', "?", '*']
VIDEO_EXTENSIONS = ['mp4', 'mpg', 'm4v', 'mov', 'mod', 'avi', '3gp', 'mkv']

# Constants for brightspace
BASE_URL = None
COOKIES = None
FORCE = None
NO_VIDEO = None

if not os.path.exists("./Downloads"): os.makedirs("./Downloads")

def get_google_token():
    if args.classroom or args.classroomall or args.listclassroom or args.google:
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            try:
                if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
            except RefreshError: get_new_google_token()
        except: get_new_google_token()
    else:
        print_em("Skipping Google sign-in (command line arguments)")

# Get a new google access token
def get_new_google_token():
    global creds

    print_warn("Google token expired. Getting new Google token...")
    print_em("Please follow the prompts on the google sign-in screen.")
    try: os.remove('token.json')
    except FileNotFoundError: pass
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=55555)
    with open('token.json', 'w') as token: token.write(creds.to_json())
    print("Done!")
    print("Continuing download...")


# Function to download a file (brightspace)
def download_bs_file(file_, path, COURSE_ID):
    r = requests.get(f'{BASE_URL}/d2l/api/le/1.51/{COURSE_ID}/content/topics/{file_["Id"]}', cookies=COOKIES)
    url_ = r.json()['Url']
    title = file_['Title'].lstrip().rstrip()
    for c in BANNED_CHARS: title = title.replace(c, '')
    print(url_)

    # If the file is stored in the Brightspace CDN
    if url_[0] == "/":
        title += "." + url_.split('.')[-1]
        if (not os.path.isfile(f"{path}{title}")) or FORCE:
            if title.lower().split('.')[-1] in VIDEO_EXTENSIONS and NO_VIDEO: pass
            else:
                print(title)
                r1 = requests.get(f'{BASE_URL}{url_}', cookies=COOKIES)
                try:
                    with open(f"{path}{title}", 'wb') as f: f.write(r1.content)
                except OSError: print_warn(f"NOT HANDLED: {url_}\n\t\t(Not downloadable as a file)")

    # If the file is stored in Google Drive
    # Also if the file is a word document being stored in Google Docs
    elif "drive.google.com" in url_ or ("docs.google.com" in url_ and "&rtpof=true&sd=true" in url_):
        if (not (os.path.isfile(f"{path}{title}") or os.path.isfile(f"{path}{title}.mp4"))) or FORCE:
            print(title)
            try: fileid = url_.split('/d/')[1].split('.')[0].split('&')[0].split('/')[0]
            except IndexError: fileid = url_.split('/open?id=')[1].split('.')[0].split('&')[0].split('/')[0]
            get_google_token()
            try:
                r1 = requests.get(f"https://www.googleapis.com/drive/v3/files/{fileid}?alt=media", headers= {'Authorization': f'Bearer {creds.token}'})
                with open(f"{path}{title}", 'wb') as f: f.write(r1.content)
            except KeyError: pass

    # If the file is a Google Doc, Sheet, or Slide
    elif "docs.google.com" in url_:
        if "document" in url_: mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"; ff = "docx"
        elif "presentation" in url_:mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"; ff = "pptx"
        elif "spreadsheet" in url_: mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"; ff = "xlsx"
        try:
            if (not os.path.isfile(f"{path}{title}.{ff}")) or FORCE:
                fileid = url_.split('/d/')[1].split('/')[0]
                print(fileid)
                get_google_token()
                try:
                    r1 = requests.get(f"https://www.googleapis.com/drive/v2/files/{fileid}/export?mimeType={mimetype}", headers= {'Authorization': f'Bearer {creds.token}'})
                    with open(f"{path}{title}.{ff}", 'wb') as f: f.write(r1.content)
                except KeyError: pass
        except UnboundLocalError: print_warn(f"Did not download f{url_}. Incompatible Google Docs file type.")


    # If the file is a Youtube video
    elif "youtu.be" in url_ or "youtube.com" in url_ and not NO_VIDEO:
        try:
            yt = YouTube(url_)
            if not os.path.isfile(f"{path}{yt.title}.mp4"):
                print(title)
                yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download(f"{path}")
        except: pass

    # Warn the user if the file was not handled by any of the above methods
    else:
        with open(f"{path}nothandled.txt", 'a') as f: f.write(str(url_) + '\n')
        print_warn(f"NOT HANDLED: {url_}")


# Function to download a folder (brightspace)
def download_bs_folder(folder, path, COURSE_ID):
    title = folder['Title'].lstrip().rstrip()
    for c in BANNED_CHARS: title = title.replace(c, '')

    r = requests.get(f'{BASE_URL}/d2l/api/le/1.51/{COURSE_ID}/content/modules/{folder["Id"]}', cookies=COOKIES)
    m = r.json()

    try:
        os.mkdir(f'{path}{title}/')
        module_desc = f"<h1>{m['Title']}<h1><br><hr><br>{m['Description']['Html']}"
        with open(f'{path}{title}/index.html', 'w') as f: f.write(module_desc)
    except FileExistsError:
        try: os.remove(f'{path}{title}/nothandled.txt')
        except FileNotFoundError: pass

    for a in m['Structure']:
        if a['Type'] == 0: download_bs_folder(a, f'{path}{title}/', COURSE_ID)
        else: download_bs_file(a, f'{path}{title}/', COURSE_ID)


# Function to download a file (in Google Classroom)
def download_gc_file(m, path, CLASS_ID):
    if 'driveFile' in m:
        try:
            url_ = m['driveFile']['driveFile']['alternateLink']
            title = m['driveFile']['driveFile']['title']
            for c in BANNED_CHARS: title = title.replace(c, '')

            # If the file is a Google Doc, Sheet, or Slide
            if "docs.google.com" in url_:
                if "document" in url_: mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"; ff = "docx"
                elif "presentation" in url_:mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"; ff = "pptx"
                elif "spreadsheet" in url_: mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"; ff = "xlsx"
                try:
                    for c in BANNED_CHARS: title = title.replace(c, '')
                    if (not os.path.isfile(f"{path}{title}.{ff}")) or FORCE:
                        fileid = url_.split('/d/')[1].split('/')[0]
                        print(fileid)
                        get_google_token()
                        try:
                            r1 = requests.get(f"https://www.googleapis.com/drive/v2/files/{fileid}/export?mimeType={mimetype}", headers= {'Authorization': f'Bearer {creds.token}'})
                            with open(f"{path}{title}.{ff}", 'wb') as f: f.write(r1.content)
                        except KeyError: pass
                        except FileNotFoundError:
                            print_err(f"An Error occurred when downlaoading {path}{title}.{ff}")
                            with open(f"./Downloads/{CLASS_ID}/errors.txt", 'a') as f: f.write(f"{path}{title}.{ff}\n")
                except UnboundLocalError: print_err(f"Could not download file: {url_}")

            # If the file is stored in Google Drive
            # Also if the file is a word document being stored in Google Docs
            elif ("drive.google.com" in url_ and "folders" not in url_) or ("docs.google.com" in url_ and "&rtpof=true&sd=true" in url_):
                if (not (os.path.isfile(f"{path}{title}") or os.path.isfile(f"{path}{title}.mp4"))) or FORCE:
                    for c in BANNED_CHARS: title = title.replace(c, '')
                    print(title)
                    try: fileid = url_.split('/d/')[1].split('.')[0].split('&')[0].split('/')[0]
                    except IndexError: fileid = url_.split('/open?id=')[1].split('.')[0].split('&')[0].split('/')[0]
                    get_google_token()
                    try:
                        r1 = requests.get(f"https://www.googleapis.com/drive/v3/files/{fileid}?alt=media", headers= {'Authorization': f'Bearer {creds.token}'})
                        with open(f"{path}{title}", 'wb') as f: f.write(r1.content)
                    except KeyError: pass
                    except FileNotFoundError:
                        print_err(f"An Error occurred when downlaoading {path}{title}.{ff}")
                        with open(f"./Downloads/{CLASS_ID}/errors.txt", 'a') as f: f.write(f"{path}{title}.{ff}\n")
        except KeyError: print_err(f"File {m['driveFile']['driveFile']['alternateLink']} has been deleted.")

    # If the file is a Youtube video
    elif 'youtubeVideo' in m:
        try:
            url_ = m['youtubeVideo']['alternateLink']
            title = m['youtubeVideo']['title']

            try:
                yt = YouTube(url_)
                if (not os.path.isfile(f"{path}{yt.title}.mp4")) and (not os.path.isfile(f"{path}{yt.title}.mov")) and (not os.path.isfile(f"{path}{yt.title}.m4v")) and (not os.path.isfile(f"{path}{yt.title}.mkv")):
                    yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download(f"{path}")
            except: pass
        except KeyError: print_err(f"Video {m['youtubeVideo']['alternateLink']} has been deleted.")

    # Warn the user if the file was not handled by any of the above methods
    else:
        print_warn(f'NOT HANDLED: {m}')


# Function to download brightspace classroom
def download_brightspace(COURSE_ID):
    print_info(f"Downloading Brightspace Classroom ({COURSE_ID})...")
    if FORCE: print_em("Force downloading... This may take a while")

    # Make base folder
    print_info("Starting Up...")
    try:
        os.mkdir(f'./Downloads/{COURSE_ID}')
    except FileExistsError: pass
    with open(f'./Downloads/{COURSE_ID}/brightspace.ct', 'w'): pass

    # Get module list
    print_info("Getting Module List...")
    r = requests.get(f'{BASE_URL}/d2l/api/le/1.51/{COURSE_ID}/content/root/', cookies=COOKIES)
    r1 = requests.get(f'{BASE_URL}/d2l/api/le/1.33/{COURSE_ID}/classlist/', cookies=COOKIES)
    r2 = requests.get(f'{BASE_URL}/d2l/lms/news/main.d2l?ou={COURSE_ID}&d2l_change=0', cookies=COOKIES)

    # Save course info, classlist, and announcements
    try:
        modules = r.json()
    except requests.exceptions.JSONDecodeError:
        print_err("ERROR: There is something wrong with the input your provided. Either the cookies are expired or the course ID and/or base URL is incorrect.")
        raise SystemExit
    with open(f'./Downloads/{COURSE_ID}/info.json', 'w') as f: json.dump(modules, f)
    try:
        classlist = r1.json()
        with open(f'./Downloads/{COURSE_ID}/classlist.json', 'w') as f: json.dump(classlist, f)
    except: requests.exceptions.JSONDecodeError: print_warn("Unable to download classlist (insufficient previleges).")
    print_info("Downloading Announcements...")
    announcements = BeautifulSoup(r2.content, 'html.parser').find_all('div', id='d_content', class_="d2l-page-main d2l-max-width d2l-min-width")[0]
    try:
        with open(f'./Downloads/{COURSE_ID}/announcements.html', 'w') as f: f.write(f"<html><body>{str(announcements).replace('<template>', '<div>').replace('</template>', '</div>')}</html></body>")
    except: print_err("Error downloading announcements")


    # Iterate through modules
    for i in modules:
        # Make folder for module
        print_em(f"Downloading {i['Title'].rstrip().lstrip()}...")
        title = i['Title'].lstrip().rstrip()
        for c in BANNED_CHARS: title = title.replace(c, '')
        try:
            os.mkdir(f"./Downloads/{COURSE_ID}/{title}")
            # Write it's title and description to HTML
            module_desc = f"<h1>{i['Title']}<h1><br><hr><br>{i['Description']['Html']}"
            with open(f'./Downloads/{COURSE_ID}/{title}/index.html', 'w') as f: f.write(module_desc)
        except FileExistsError:
            try: os.remove(f'{COURSE_ID}/{title}/nothandled.txt')
            except FileNotFoundError: pass

        for a in i['Structure']:
            if a['Type'] == 0: download_bs_folder(a, f'./Downloads/{COURSE_ID}/{title}/', COURSE_ID)
            else: download_bs_file(a, f'./Downloads/{COURSE_ID}/{title}/', COURSE_ID)
        print_succ(f"Successfully downloaded module \"{i['Title'].rstrip().lstrip()}\"")


# Function to download google classroom
def download_classroom(CLASS_ID):
    # Make base folder
    print_info("Starting Up...")
    try:
        os.mkdir(f'./Downloads/{CLASS_ID}')
    except FileExistsError: pass
    with open(f'./Downloads/{CLASS_ID}/classroom.ct', 'w'): pass

    try: os.remove(f"./Downloads/{CLASS_ID}/errors.txt")
    except FileNotFoundError: pass

    # Download class data and save it to JSON files
    print_info('Downloading class info...')
    r = requests.get(f"https://classroom.googleapis.com/v1/courses/{CLASS_ID}", headers= {'Authorization': f'Bearer {creds.token}'})
    with open(f'./Downloads/{CLASS_ID}/info.json', 'w') as f: json.dump(r.json(), f)
    print_info('Downloading student list...')
    r1 = requests.get(f"https://classroom.googleapis.com/v1/courses/{CLASS_ID}/students?pageSize=1000", headers= {'Authorization': f'Bearer {creds.token}'})
    with open(f'./Downloads/{CLASS_ID}/classlist.json', 'w') as f: json.dump(r1.json(), f)
    print_info('Downloading teacher list...')
    r2 = requests.get(f"https://classroom.googleapis.com/v1/courses/{CLASS_ID}/teachers?pageSize=1000", headers= {'Authorization': f'Bearer {creds.token}'})
    with open(f'./Downloads/{CLASS_ID}/teacherlist.json', 'w') as f: json.dump(r2.json(), f)
    print_info('Downloading topic list...')

    # Download announcements
    print_info('Downloading announcements...')
    r3 = requests.get(f"https://classroom.googleapis.com/v1/courses/{CLASS_ID}/announcements", headers= {'Authorization': f'Bearer {creds.token}'})
    with open(f'./Downloads/{CLASS_ID}/announcements.json', 'w') as f: json.dump(r3.json(), f)
    if 'announcements' in r3.json():
        for i in r3.json()['announcements']:
            if 'materials' in i:
                print(i['materials'])
                # Create folders if they don't exist
                if not os.path.exists(f'./Downloads/{CLASS_ID}/Announcements/'): os.mkdir(f'./Downloads/{CLASS_ID}/Announcements/')
                # Clean path names
                mat = i['id']
                mat = mat.replace('\n', ' ')
                for c in BANNED_CHARS: mat = mat.replace(c, '')
                path = f'./Downloads/{CLASS_ID}/Announcements/{mat}/'

                try:
                    if not os.path.exists(path): os.mkdir(path)

                    # Iterate through all the materials and download any files
                    for m in i['materials']:
                        download_gc_file(m, path, CLASS_ID)
                except FileNotFoundError: pass

    # Download topics
    r4 = requests.get(f"https://classroom.googleapis.com/v1/courses/{CLASS_ID}/topics", headers= {'Authorization': f'Bearer {creds.token}'})
    with open(f'./Downloads/{CLASS_ID}/topics.json', 'w') as f: json.dump(r4.json(), f)
    topics = {}
    try:
        for t in r4.json()['topic']:
            temp = t['name']
            for c in BANNED_CHARS: temp = temp.replace(c, '')
            topics[t['topicId']] = temp
    except KeyError: pass

    # Download materials
    print_em('Downloading materials...')
    r5 = requests.get(f"https://classroom.googleapis.com/v1/courses/{CLASS_ID}/courseWorkMaterials", headers= {'Authorization': f'Bearer {creds.token}'})
    with open(f'./Downloads/{CLASS_ID}/materials.json', 'w') as f: json.dump(r5.json(), f)
    # Look for attached files
    if 'courseWorkMaterial' in r5.json():
        for i in r5.json()['courseWorkMaterial']:
            if 'materials' in i:
                try: top_ = topics[i["topicId"]]
                except KeyError: top_ = "NO TOPIC"

                # Create folders if they don't exist
                if not os.path.exists(f'./Downloads/{CLASS_ID}/Materials/'): os.mkdir(f'./Downloads/{CLASS_ID}/Materials/')
                print_info('Downloading attachments for ' + i['title'].replace('\n', ' ') + '...')
                if not os.path.exists(f'./Downloads/{CLASS_ID}/Materials/{top_}/'): os.mkdir(f'./Downloads/{CLASS_ID}/Materials/{top_}/')
                # Clean path names
                mat = i['title']
                mat = mat.replace('\n', ' ')
                for c in BANNED_CHARS: mat = mat.replace(c, '')
                path = f'./Downloads/{CLASS_ID}/Materials/{top_}/{mat}/'

                try:
                    if not os.path.exists(path): os.mkdir(path)

                    # Iterate through all the materials and download any files
                    for m in i['materials']:
                        download_gc_file(m, path, CLASS_ID)
                except FileNotFoundError: pass

    # Download classwork
    print_em('Downloading classwork...')
    r6 = requests.get(f"https://classroom.googleapis.com/v1/courses/{CLASS_ID}/courseWork", headers= {'Authorization': f'Bearer {creds.token}'})
    with open(f'./Downloads/{CLASS_ID}/coursework.json', 'w') as f: json.dump(r6.json(), f)
    # Look for attached files
    if 'courseWork' in r6.json():
        for i in r6.json()['courseWork']:
            if 'materials' in i:
                try: top_ = topics[i["topicId"]]
                except KeyError: top_ = "NO TOPIC"

                # Create folders if they don't exist
                if not os.path.exists(f'./Downloads/{CLASS_ID}/Classwork/'): os.mkdir(f'./Downloads/{CLASS_ID}/Classwork/')
                print_info('Downloading attachments for ' + i['title'].replace('\n', ' ') + '...')
                if not os.path.exists(f'./Downloads/{CLASS_ID}/Classwork/{top_}/'): os.mkdir(f'./Downloads/{CLASS_ID}/Classwork/{top_}/')
                # Clean path names
                mat = i['title']
                mat = mat.replace('\n', ' ')
                for c in BANNED_CHARS: mat = mat.replace(c, '')
                path = f'./Downloads/{CLASS_ID}/Classwork/{top_}/{mat}/'

                try:
                    if not os.path.exists(path): os.mkdir(path)

                    # Iterate through all the materials and download any files
                    for m in i['materials']:
                        download_gc_file(m, path, CLASS_ID)
                except FileNotFoundError: pass


def list_brightspace():
    r = requests.get(f"{BASE_URL}/d2l/api/lp/1.35/enrollments/myenrollments/", cookies=COOKIES)
    courses = {"courses": [i for i in r.json()["Items"] if i['OrgUnit']['Type']['Name'] == "Course Offering"]}

    print(tabulate([[i['OrgUnit']['Name'], i['OrgUnit']['Id'], "ACTIVE" if i['Access']['IsActive'] else "INACTIVE"] for i in courses["courses"]], headers=['Name', 'ID', 'Active'], tablefmt='orgtbl'))
    with open(f'./Downloads/courses.json', 'w') as f: json.dump(courses, f)


def brightspace_all():
    r = requests.get(f"{BASE_URL}/d2l/api/lp/1.35/enrollments/myenrollments/", cookies=COOKIES)
    courses = {"courses": [i for i in r.json()["Items"] if i['OrgUnit']['Type']['Name'] == "Course Offering"]}

    for i in courses["courses"]:
        print_em(f"Downloading classroom: {i['OrgUnit']['Name']}")
        download_brightspace(i['OrgUnit']['Id'])


def check_brightspace_args():
    global BASE_URL
    global COOKIES
    global FORCE
    global NO_VIDEO
    
    if args.baseurl: BASE_URL = args.baseurl
    else: print_err("Please specify a base URL for Brightspace."); raise SystemExit
    if args.cookies:
        with open(args.cookies) as f:
            c_ = json.loads(f.read())
            COOKIES = {i['name']: i['value'] for i in c_}
            print_info(f"Getting cookies from stored file ({args.cookies}).")
    else:
        if args.securesession and args.session:
            COOKIES = {'d2lSecureSessionVal': args.securesession, 'd2lSessionVal': args.session}
            print_info("Getting cookies from arguments. Note that this may not work in instances that use 2FA.")
        else: print_err("Please provide session ID's or a cookie file link."); raise SystemExit

    if args.force: FORCE = True
    else: FORCE = False

    if args.novideo: NO_VIDEO = True
    else: NO_VIDEO = False

    if args.google: get_google_token()

def check_google_args():
    if args.force: FORCE = True
    else: FORCE = False

    # Get a new google token if required
    get_google_token()


def get_input(input_prompt, options, first_prompt=None, error_prompt=None):
    inp = None
    first = True
    while (inp not in options):
        if True in options and not first: break
        if not first and error_prompt: print_err(error_prompt)
        if first_prompt and first: print_info(first_prompt)

        inp = input(input_prompt).lower().lstrip().rstrip()
        first = False
    
    print()
    return inp


start = time.time()

print("\n".join(SPLASH_TEXT) + "\n\n")

if args.interactive:
    while True:
        print_em("Welcome to Singularity!")
        inp_dlt = get_input(
            "Please enter \"bs\" for Brightspace or \"gc\" for Google Classroom: ",
            ['gc', 'bs', 'classroom', 'brightspace'],
            "What type of class would you like to download?",
            "Please enter one of the valid options"
        )

        if inp_dlt in ["bs", "brightspace"]:
            while True:
                inp_burl = get_input(
                    "Please enter the full Base URL [for example: \"https://example.com\"]: ",
                    [True],
                    "What is the Base URL for the Brightspace instance?"
                )
                if inp_burl[-1] == "/": inp_burl = inp_burl[:-1]
                try:
                    r = requests.get(inp_burl)
                    _ = r.text
                    break
                except: print_err("You did not enter a valid URL that could be queried. Please try again.")

            inp_authtype = get_input(
                "Please enter \"v\" to provide cookie values or \"f\" to provide a file: ",
                ['v', 'f'],
                "How would you like to authenticate with Brightspace? Note that value-based authentication may not work in instances with 2FA.",
                "Please enter \"v\" or \"f\""
            )

            if inp_authtype == "v":
                print_em("You have chosen value based authentication")
                print_warn("This method might not work in some instances of Brightspace, especially those with 2FA. Proceed with caution.")
                print("You will need to get cookies from the Brightspace instance from your browser. Please see the README file for more information.")
                print_warn("DO NOT share these cookies ANYWHERE else, and copy something else to your clipboard once you have pasted the cookies here.\n")

                inp_sv = get_input(
                    "Please enter the value of the cookie \"d2lSessionVal\": ",
                    [True],
                )
                
                inp_ssv = get_input(
                    "Please enter the value of the cookie \"d2lSecureSessionVal\": ",
                    [True],
                )
                
            elif inp_authtype == "f":
                print_em("You have chosen file based authentication")
                print("You will need to export cookies from Brightspace to a JSON file. Please see the README file for more information.")
                print_warn("DO NOT share these cookies ANYWHERE else, and delete the cookies file once the program finishes executing.\n")

                while True:
                    inp_cf = get_input(
                        "Please enter the name of the cookies file (must be in the same directory as this program): ",
                        [True],
                    )
                    try:
                        with open(inp_cf) as f: c_ = json.loads(f.read())
                        break
                    except: print_err("The file provided is not a valid JSON file or does not exist.")
            
            BASE_URL = inp_burl
            if inp_authtype == "f":
                with open(inp_cf) as f:
                    c_ = json.loads(f.read())
                    COOKIES = {i['name']: i['value'] for i in c_}
            elif inp_authtype == "v":
                COOKIES = {'d2lSecureSessionVal': args.securesession, 'd2lSessionVal': args.session}
            

            print_info(f"You are connected to the Brightspace instance [{inp_burl}] and are authenticated with {'values' if inp_authtype == 'v' else 'a cookies file'}.")
            print("Please enter \"course\" to download a course, \"list\" to list all courses, \"all\" to download all, \"help\" to display this message again and \"exit\" to exit")
            while True:
                inp_prompt = input("> ").lower().lstrip().rstrip()
                
                if inp_prompt == "list":
                    list_brightspace()

                elif inp_prompt in ["course", "all"]:
                    inp_force = get_input(
                        "Please enter \"y\" for yes and \"n\" for no: ",
                        ["y", "n"],
                        "Do you want to force re-download everything? This only has an effect if you have downloaded this course before."
                    )
                    FORCE = (inp_force == "y")

                    inp_video = get_input(
                        "Please enter \"y\" for yes and \"n\" for no: ",
                        ["y", "n"],
                        "Do you want to download videos? This can significantly increase the time and space taken to download."
                    )
                    NO_VIDEO = (inp_video == "n")

                    inp_google = get_input(
                        "Please enter \"y\" for yes and \"n\" for no: ",
                        ["y", "n"],
                        "Do you want to sign in to Google? This is required to download private Google Drive files shared only to students."
                    )
                    if inp_google == "y": get_google_token()

                    if inp_prompt == "course":
                        inp_course = int(get_input(
                            "Please enter the course ID: ",
                            [True],
                            "Please provide the Course ID for the course you want to download.\nThis is the nunber at the end of the Brightspace URL, or can be found in the ID column of the course list"
                        ))
                        download_brightspace(inp_course)

                    elif inp_prompt == "all":
                        brightspace_all()

                elif inp_prompt == "help":
                    print("Please enter \"course\" to download a course, \"list\" to list all courses, \"all\" to download all, \"help\" to display this message again and \"exit\" to exit")

                elif inp_prompt == "exit":
                    print_em("Exiting Singularity...")
                    raise SystemExit

                else:
                    print_err("Please enter a valid option. Enter \"help\" to display a help message")

        
        elif inp_dlt in ["gc", "classroom"]:
            print_err("Interactive mode has not yet been implemented for Google Classroom. Please use command line arguments for now")
            raise NotImplementedError

# Download a brightspace classroom if the argument is set
elif args.brightspace:
    check_brightspace_args()

    if args.course: COURSE_ID = args.course
    else: print_err("Please specify a brightspace course ID."); raise SystemExit

    download_brightspace(COURSE_ID)

elif args.brightspaceall:
    check_brightspace_args()

    brightspace_all()


elif args.listbrightspace:
    check_brightspace_args()

    list_brightspace()

# Download a google classroom if the argument is set
elif args.classroom:
    check_google_args()

    if args.classid: CLASS_ID = args.classid
    else: print_err("Please specify a class ID for Google Classroom."); raise SystemExit

    download_classroom(CLASS_ID)

elif args.classroomall:
    check_google_args()

    # List all classes in classroom
    r = requests.get(f"https://classroom.googleapis.com/v1/courses", headers= {'Authorization': f'Bearer {creds.token}'})
    cls = r.json()['courses']
    for i in cls:
        print_em(f'Downloading classroom: {i["name"]}')
        download_classroom(i['id'])

elif args.listclassroom:
    check_google_args()

    # List all classes in classroom
    r = requests.get(f"https://classroom.googleapis.com/v1/courses", headers= {'Authorization': f'Bearer {creds.token}'})
    cls = r.json()['courses']
    print(tabulate([[i['name'], i['id'], i['courseState']] for i in cls], headers=['Name', 'ID', 'Active'], tablefmt='orgtbl'))
    with open(f'./Downloads/classrooms.json', 'w') as f: json.dump(r.json(), f)

else:
    parser.print_help(sys.stderr)
    print_err("Please provide the required arguments.")
    raise SystemExit

if not args.interactive:
    print_succ(ef.bold + f" DONE! {time.time() - start:.2f} seconds." + rs.bold_dim)
