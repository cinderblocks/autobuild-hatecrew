#!/usr/bin/python
"""\
@file   connection.py
@author Nat Goodspeed
@date   2010-04-20
@brief  Classes shared between package.py and upload.py

$LicenseInfo:firstyear=2010&license=internal$
Copyright (c) 2010, Linden Research, Inc.
$/LicenseInfo$
"""

import os
import sys
import glob
import urllib2
import subprocess
import common
import boto.s3.connection

AutobuildError = common.AutobuildError

class ConnectionError(AutobuildError):
    def __init__(self,msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)

class S3ConnectionError(ConnectionError):
    pass

class SCPConnectionError(ConnectionError):
    pass

#
# Talking to remote servers
#

class Connection(object):
    """Shared methods for managing connections.
    """
    def fileExists(self, url):
        """Test to see if file exists on server.  Returns boolean.
        """
        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                return False
            raise
        else:
            return True

class SCPConnection(Connection):
    """Manage uploading files.  Never overwrite existing files.
    """
    def __init__(self, server="install-packages.lindenlab.com",
                 dest_dir="/local/www/install-packages/doc"):
        self.setDestination(server, dest_dir)

    # *TODO: make this method 'static'?
    # *TODO: fix docstring -- current docsctring should be comment in Pkg class
    def upload(self, files, server=None, dest_dir=None, dry_run=False):
        """Do this for all packages all the time!
        This is how we maintain backups of tarfiles(!!!).  Very important.
        @param filename Fully-qualified name of file to be uploaded
        """
        uploadables = []
        for file in files:
            if self.SCPFileExists(file, server, dest_dir):
                print ("Info: A file with name '%s' in dir '%s' already exists on %s. Not uploading." % (self.basename, self.dest_dir, self.server))
            else:
                uploadables.append(file)
        if uploadables:
            print "Uploading to: %s" % self.scp_dest
            command = [common.get_default_scp_command()] + uploadables + [self.scp_dest]
            if dry_run:
                print " ".join(command)
            else:
                subprocess.call(command) # interactive -- possible password req'd

    def SCPFileExists(self, filename, server=None, dest_dir=None):
        """Set member vars and check if file already exists on dest server.
        @param filename Full path to file to be uploaded.
        @param server If provided, specifies server to upload to.
        @param dest_dir If provided, specifies destination directory on server.
        @return Returns boolean indicating whether file exists on server.
        """
        self.setDestination(server, dest_dir)
        self.loadFile(filename)
        return self.fileExists(self.url)

    def setDestination(self, server, dest_dir):
        """Set destination to dest_dir on server."""
        if server:
            self.server = server
        if dest_dir != None:  # allow: == ""
            self.dest_dir = dest_dir
        if not self.server or self.dest_dir == None:
            raise SCPConnectionError("Both server and dest_dir must be set.")
        self.scp_dest = ':'.join([self.server, self.dest_dir])

    def getSCPUrl(self, filename):
        """Return the url the pkg would be at if on the server."""
        self.loadFile(filename)
        return self.SCPurl

    def loadFile(self, filename):
        """Set member vars based on filename."""
        self.filename = filename
        self.basename = os.path.basename(filename)
        # at final location, should be in root dir of served dir
        self.url = "http://" + self.server + "/" + self.basename
        self.SCPurl = "scp:" + self.scp_dest + "/" + self.basename


class S3Connection(Connection):
    """Twiddly bits of talking to S3.  Hi S3!
    """
    # keep S3 url http instead of https
    amazonS3_server = "http://s3.amazonaws.com/"
    S3_upload_params = dict(
                            id="1E4G7QTW0VT7Z3KJSJ02",
                            key="GuchuxQF1ADPCz3568ADS/Vc5bds807e7pj1ybU+",
                            acl="public-read",
                       )

    def __init__(self, S3_dest_dir="viewer-source-downloads/install_pkgs"):
        """Set server dir for all transactions.
        Alternately, use member methods directly, supplying S3_dest_dir.
        """
        # here by design -- server dir should be specified explicitly
        self.connection = boto.s3.connection.S3Connection(self.S3_upload_params["id"],
                                                          self.S3_upload_params["key"])
        # in case S3_dest_dir is explicitly passed as None
        self.bucket = None
        self.partial_key = ""
        # initialize self.bucket, self.partial_key
        self.setS3DestDir(S3_dest_dir)

    def _get_key(self, pathname):
        """
        @param pathname Local filesystem pathname for which to get the
        corresponding S3 key object. Relies on the current self.bucket and
        self.partial_key (from S3_dest_dir). Extracts just the basename from
        pathname and glues it onto self.partial_key.
        """
        if self.bucket is None:
            # This object was initialized with S3_dest_dir=None, and we've
            # received no subsequent setS3DestDir() call with a non-None value.
            raise S3ConnectionError("Error: S3 destination directory must be set.")
        # I find new_key() a somewhat misleading method name: it doesn't have
        # any effect on S3; it merely instantiates a new Key object tied to
        # the bucket on which you make the call.
        return self.bucket.new_key('/'.join((self.partial_key, os.path.basename(pathname))))

    def upload(self, filename, S3_dest_dir=None, dry_run=False):
        """Upload file specified by filename to S3.
        If file already exists at specified destination, raises exception.
        NOTE:  Knowest whither thou uploadest! Ill fortune will befall
        those who upload blindly.
        """
        if S3_dest_dir is not None:
            self.setS3DestDir(S3_dest_dir)
        # Get the S3 key object on which we can perform operations.
        key = self._get_key(filename)
        if key.exists():
            raise S3ConnectionError("A file with name '%s/%s' already exists on S3. Not uploading."
                                    % (self.bucket.name, key.name))

        print "Uploading to: %s" % self.getUrl(filename)
        if not dry_run:
            key.set_contents_from_filename(filename)
            key.set_acl(self.S3_upload_params["acl"])

    def S3FileExists(self, filename):
        """Check if file exists on S3.
        @param filename Filename (incl. path) of file to be uploaded.
        @return Returns boolean indicating whether file already exists on S3.
        """
        return self._get_key(filename).exists()

    def setS3DestDir(self, S3_dest_dir):
        """Set class vars for the destination dir on S3."""
        if S3_dest_dir is None:  # allow: == ""
            return
        # We don't actually store S3_dest_dir itself any more. The important
        # side effect of setting S3_dest_dir is to set self.bucket and
        # self.partial_key.
        # To get the bucket name, split off only before the FIRST slash.
        bucketname, self.partial_key = S3_dest_dir.split('/', 1)
        self.bucket = self.connection.get_bucket(bucketname)

    def getUrl(self, filename):
        """Return the url the pkg would be at if on the server."""
        key = self._get_key(filename)
        return "%s%s/%s" % (self.amazonS3_server + self.bucket.name + self._get_key(filename).name)