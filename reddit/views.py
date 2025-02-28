from django.http import HttpResponse
from django.shortcuts import render
from dotenv import load_dotenv
from praw import Reddit
import os
import prawcore
load_dotenv()

def get_reddit_instance(refresh_token=None):
    return Reddit(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("SECRET"),
        user_agent=os.getenv("USER_AGENT"),
        redirect_uri="http://localhost:8000/reddit/", # Make sure this is your redirect uri in app
        refresh_token=refresh_token,
        ratelimit_seconds=300
    )

def fetch_subreddit(reddit, subreddit_name):
    #Fetch subreddit data and handle errors
    try:
        subreddit = reddit.subreddit(subreddit_name).hot(limit=5) #get the top 5 posts on the given subreddit
        post_list = list(subreddit) #turn into a list and check if posts exist, if not sub doesn't have posts/doesn't exist 
        if not post_list:
            return None, f"The subreddit 'r/{subreddit_name}' exists but has no posts."
        return post_list, None # return the list, and error=None
    except prawcore.exceptions.NotFound: # checks if subreddit exists
        return None, f"The subreddit 'r/{subreddit_name}' does not exist." # if error exist set subreddit as None and erturn the error
    except Exception as e: # other errors
        return None, f"Error accessing r/{subreddit_name}: {str(e)}"


def app(req):
    refresh_token = req.session.get('reddit_refresh_token') # get token from session if exists
    reddit = get_reddit_instance(refresh_token)
    code = req.GET.get('code', None)

    # Handle auth if code is present and token isn't
    if code and not refresh_token:
        try:
            refresh_token = reddit.auth.authorize(code) # creates token 
            req.session['reddit_refresh_token'] = refresh_token # stores token in a session
            reddit = get_reddit_instance(refresh_token)  # reinitialize setings with new token
        except Exception as e: # handle errors
            return HttpResponse(f"Error during Reddit authentication: {e}")

    # If no refresh token and no code, prompt for auth
    if not refresh_token:
        auth_url = reddit.auth.url(scopes=["identity", "read"], state="unique_state_string", duration="permanent")
        return HttpResponse(f"<a href='{auth_url}'>Authorize</a>")

    try:
        reddit_user = reddit.user.me() # if exists user is logged in
    except Exception as e:
        reddit_user = "None"
        req.session.pop('reddit_refresh_token', None) # if there is no, user remove token and authenticate again
        return HttpResponse(f"Error with stored credentials: {e}. Please reauthorize.")

    # Determine subreddit name from POST or default to "all"
    subreddit_name = req.POST.get("sub", "all") if req.method == "POST" else "all"
    subreddit, error = fetch_subreddit(reddit, subreddit_name)

    return render(req, "index.html", {"reddit_user": reddit_user,"subreddit": subreddit,"error": error, "subreddit_name": subreddit_name})