import aiohttp

class GithubError(Exception):
    """Thrown when a Github API operation fails.
    """
    pass


async def getNewestTagOnRemote(httpClient: aiohttp.ClientSession, url: str) -> str:
    """Fetch the name of the latest tag on the given git remote.
    If the remote has no tags, empty string is returned.

    :param aiohttp.ClientSession httpClient: The ClientSession to request git info with
    :param str url: URL to the git remote to check
    :return: String name of the the latest tag on the remote at URL, if the remote at URL has any tags. Empty string otherwise
    :rtype: str 
    """
    async with httpClient.get(url) as resp:
        try:
            resp.raise_for_status()
            respJSON = await resp.json()
            return respJSON[0]["tag_name"]
        except (IndexError, KeyError, aiohttp.ContentTypeError, aiohttp.ClientResponseError):
            raise GithubError("Could not fetch latest release info from GitHub. Is the GitHub API down?")
            