# Singularity
Singularity is a command-line script written in Python that can download content, announcements, and more from Google Classroom or D2L Brightspace to a local directory in standardized file formats.

## Why does it exist?
Towards the end of my final year in high school, many of my teachers suggested that I keep a copy of all the notes and slides that they created, as it can be a useful reference during post secondary education. But since our online accounts would be deleted when we graduate, I could not rely on accessing it directly through the learning platforms. So, I made this program to download a local copy of all the data from online classroom websites so that I could keep a copy of learning resources even after I graduated.

## What does it do?
Here are some things that Singularity can do:
- Download all content, announcements, and other data from Google Classroom and D2L Brigtspace classes.
- Download almost all possible file types stored in a myriad of different sources, and provide a list of any files that could not be downloaded.
- Run in the background without any human intervention needed.
- Automatically pick up where it left off if interrupted.

## How to run it?
*NOTE: Singularity NEEDS Python 3 in order to run*
1. Install the required packages.

    `pip install -r requirements.txt` OR `pip3 install -r requirements.txt`

2. Set up access credentials.
    - If you are downloading a **Google Classroom** class or any **Google Drive** links, you will need to set up a Google API key and store it in `credentials.json`. I will add a more detailed tutorial for this later.

    - If you are downloading a **Brightspace class**, then you need to provide cookies for authentication. This can be done in two different ways. One way is to copy the `d2lSessionVal` and `d2lSecureSessionVal` cookies from your web browser (make sure you are signed in to the Brightspace instance before you do this) and provide them as command line arguments as `-sv` and `-ssv` respectively. While this approach works from many Brightspace instances, many instances that use 2FA, especially those of universities, need more cookies for authentication. Since the names of these cookies aren't standardized, you need to export all the cookies your browser has for the Brightspace instance to a file. I recommend using [**this Chrome extension**](https://chrome.google.com/webstore/detail/nmckokihipjgplolmcmjakknndddifde) to export the cookies. Once you have the file, make sure to save it in the same folder as `singularity.py` and provide the file name using the command line argument `-cf`. If you are unsire what authentication method to use, I would recommend the second option. Please note that these cookies are **highly confidential** and **should not** be shared with **anyone else**.

3. Make sure your computer is ready for the download.
    - Depending on the size of the class, the time and download size can vary greatly. Some classes can take 15 seconds to download and use up a few megabytes of space, while other classes can take hours or days to download and can use up tens to hundreds of gigabytes of space. There are some command line arguments to customize the types of files downloaded. Irrespective of the size of your download, please make sure that your computer is connected to power, and has a reliable, preferrably unlimited, internet connection.

4. Run Singularity.  
    `python singularity.py <arguments>` or `python3 singularity.py <arguments>`  
    More information on the arguments to use is provided below.

## Command Line Arguments
Arguments for determining Download type. All of these arguments are boolean (provide argument only):
- `-bs`: Download a single Brightspace classroom.
- `-bsa`: Download all available Brightspace classrooms.
- `-lb`: List all Brightspace classrooms.
- `-gc`: Download a single Google Classroom class.
- `-gca`: Download all available Google Classroom classes (even archived ones).
- `-lc`: List all Google Classroom classes.
- `-i`: Launch interactive mode (currently available for Brightspace only).

Arguments for Brightspace only. These arguments are either boolean (provide argument only) or values (provide argument and value):
- `-c`: Brightspace Course ID *[value]*.
- `-ssv`: Secure Session Value cookie *[value]*.
- `-sv`: Session Value cookie *[value]*.
- `-cf`: Cookies JSON file name *[value]*.
- `-bu`: Base URL of Brightspace instance *[value]*.
- `-gg`: Sign in to Google (required to save provate Google Drive files) *[boolean]*.
- `-nv`: Don't download any videos (saves space and decreases download time) *[boolean]*.

Arguments for Google Classroom only.
- `-cid`: Google Classroom class ID *[value]*.

Common arguments for both Brightspace and Google Classroom:
- `-f`: Force redownload all files *[boolean]*.

In order to run Singularity, you will need to format a command like this:

`python[3] singularity.py <download_type> <args>`

Where `<download_type>` is **ONE** of the download type arguments, and `<args>` is all the required arguments for the chosen download type. If you are using *interactive mode* (`-i`), then you **shouldn't** provide ANY other arguments.

Here are some examples:
- Download a Brightspace classroom: `python[3] singularity.py -bs -c 12345 -cf cookies.json -bu https://example.com/`  
This command downloads the class with ID `12345` from the Brightspace instance hosted at `https://example.com/` by authenticating with the cookie file `cookies.json`.
- Download Google Classroom class: `python[3] singularity.py -gc -cid 12345678`  
This command downloads the class with ID `12345678` from Google Classroom (note that you need to have valid API access credentials to be able to use Google Classroom).
- Launch interactive mode: `python[3] singularity.py -i`  
This command launches interactive mode.

## Future improvements
These are some features that will (hopefully) be implemented soon when I can find the time. If you are interested in this sort of thing and have some free time on your hands, feel free to implement any of these, or anything else that you feel can add value to Singularity, and submit a pull request.
- Better login to Brightspace (Using username and password and allowing 2FA).
- More customizability for download options (ex. video quality, download speed, include or exclude files with regex, etc.).
- Ability to access functions from other programs (as a library).
- Multi-threading for faster downloads.
- Distributed downloads across multiple computers.
- Ability to provide input with a configuration file.
