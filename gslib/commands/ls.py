# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gslib.bucket_listing_ref import BucketListingRef
from gslib.command import Command
from gslib.command import COMMAND_NAME
from gslib.command import COMMAND_NAME_ALIASES
from gslib.command import CONFIG_REQUIRED
from gslib.command import FILE_URIS_OK
from gslib.command import MAX_ARGS
from gslib.command import MIN_ARGS
from gslib.command import PROVIDER_URIS_OK
from gslib.command import SUPPORTED_SUB_ARGS
from gslib.command import URIS_START_ARG
from gslib.exception import CommandException
from gslib.help_provider import HELP_NAME
from gslib.help_provider import HELP_NAME_ALIASES
from gslib.help_provider import HELP_ONE_LINE_SUMMARY
from gslib.help_provider import HELP_TEXT
from gslib.help_provider import HelpType
from gslib.help_provider import HELP_TYPE
from gslib.util import ListingStyle
from gslib.util import MakeHumanReadable
from gslib.util import NO_MAX
from gslib.wildcard_iterator import ContainsWildcard
import boto

_detailed_help_text = ("""
<B>SYNOPSIS</B>
  gsutil ls [-b] [-l] [-L] [-R] [-p proj_id] uri...


<B>LISTING PROVIDERS, BUCKETS, SUBDIRECTORIES, AND OBJECTS</B>
  If you run gsutil ls without URIs, it lists all of the Google Cloud Storage
  buckets under your default project ID:

    gsutil ls

  (For details about projects, see "gsutil help projects" and also the -p
  option in the OPTIONS section below.)

  If you specify one or more provider URIs, gsutil ls will list buckets at
  each listed provider:

    gsutil ls gs://

  If you specify bucket URIs, gsutil ls will list objects at the top level of
  each bucket, along with the names of each subdirectory. For example:

    gsutil ls gs://bucket

  might produce output like:

    gs://bucket/obj1.htm
    gs://bucket/obj2.htm
    gs://bucket/images1/
    gs://bucket/images2/

  The "/" at the end of the last 2 URIs tells you they are subdirectories,
  which you can list using:

    gsutil ls gs://bucket/images*

  If you specify object URIs, gsutil ls will list the specified objects. For
  example:

    gsutil ls gs://bucket/*.txt

  will list all files whose name matches the above wildcard at the top level
  of the bucket.

  See "gsutil help wildcards" for more details on working with wildcards.


<B>DIRECTORY BY DIRECTORY, FLAT, and RECURSIVE LISTINGS</B>
  Listing a bucket or subdirectory (as illustrated near the end of the previous
  section) only shows the objects and names of subdirectories it contains. You
  can list all objects in a bucket by using the -R option. For example:

    gsutil ls -R gs://bucket

  will list the top-level objects and buckets, then the objects and
  buckets under gs://bucket/images1, then those under gs://bucket/images2, etc.

  If you want to see all objects in the bucket in one "flat" listing use the
  recursive ("**") wildcard, like:

    gsutil ls -R gs://bucket/**

  or, for a flat listing of a subdirectory:

    gsutil ls -R gs://bucket/dir/**


<B>LISTING OBJECT DETAILS</B>
  If you specify the -l option, gsutil will output additional information
  about each matching provider, bucket, subdirectory, or object. For example,

    gsutil ls -l gs://bucket/*.txt

  will print the object size, creation time stamp, and name of each matching
  object, along with the total count and sum of sizes of all matching objects:

       2276224  2012-03-02T19:25:17  gs://bucket/obj1
       3914624  2012-03-02T19:30:27  gs://bucket/obj2
    TOTAL: 2 objects, 6190848 bytes (5.9 MB)

  Note that the total listed in parentheses above is in mebibytes (or gibibytes,
  tebibytes, etc.), which corresponds to the unit of billing measurement for
  Google Cloud Storage.

  You can get a listing of all the objects in the top-level bucket directory
  (along with the total count and sum of sizes) using a command like:

    gsutil ls -l gs://bucket

  To print additional detail about objects and buckets use the gsutil ls -L
  option. For example:

    gsutil ls -L gs://bucket/obj1

  will print something like:

    gs://bucket/obj1:
            Object size:	2276224
            Last mod:	Fri, 02 Mar 2012 19:25:17 GMT
            Cache control:	private, max-age=0
            MIME type:	application/x-executable
            Etag:	5ca6796417570a586723b7344afffc81
            ACL:	<Owner:00b4903a97163d99003117abe64d292561d2b4074fc90ce5c0e35ac45f66ad70, <<UserById: 00b4903a97163d99003117abe64d292561d2b4074fc90ce5c0e35ac45f66ad70>: u'FULL_CONTROL'>>
    TOTAL: 1 objects, 2276224 bytes (2.17 MB)

  Note that the -L option is slower and more costly to use than the -l option,
  because it makes a bucket listing request followed by a HEAD request for
  each individual object (rather than just parsing the information it needs
  out of a single bucket listing, the way the -l option does).

  See also "gsutil help getacl" for getting a more readable version of the ACL.


<B>LISTING BUCKET DETAILS</B>
  If you want to see information about the bucket itself, use the -b
  option. For example:

    gsutil ls -L -b gs://bucket

  will print something like:

    gs://bucket/ :
            24 objects, 29.83 KB
            LocationConstraint: US
            ACL: <Owner:00b4903a9740e42c29800f53bd5a9a62a2f96eb3f64a4313a115df3f3a776bf7, <<GroupById: 00b4903a9740e42c29800f53bd5a9a62a2f96eb3f64a4313a115df3f3a776bf7>: u'FULL_CONTROL'>>
            Default ACL: <>
    TOTAL: 24 objects, 30544 bytes (29.83 KB)


<B>OPTIONS</B>
  -l          Prints long listing (owner, length).

  -L          Prints even more detail than -L. This is a separate option because
              it makes additional service requests (so, takes longer and adds
              requests costs).

  -b          Prints info about the bucket when used with a bucket URI.

  -p proj_id  Specifies the project ID to use for listing buckets.

  -R, -r      Requests a recursive listing.
""")


class LsCommand(Command):
  """Implementation of gsutil ls command."""

  # Command specification (processed by parent class).
  command_spec = {
    # Name of command.
    COMMAND_NAME : 'ls',
    # List of command name aliases.
    COMMAND_NAME_ALIASES : ['dir', 'list'],
    # Min number of args required by this command.
    MIN_ARGS : 0,
    # Max number of args required by this command, or NO_MAX.
    MAX_ARGS : NO_MAX,
    # Getopt-style string specifying acceptable sub args.
    SUPPORTED_SUB_ARGS : 'blLp:rR',
    # True if file URIs acceptable for this command.
    FILE_URIS_OK : False,
    # True if provider-only URIs acceptable for this command.
    PROVIDER_URIS_OK : True,
    # Index in args of first URI arg.
    URIS_START_ARG : 0,
    # True if must configure gsutil before running command.
    CONFIG_REQUIRED : True,
  }
  help_spec = {
    # Name of command or auxiliary help info for which this help applies.
    HELP_NAME : 'ls',
    # List of help name aliases.
    HELP_NAME_ALIASES : ['dir', 'list'],
    # Type of help:
    HELP_TYPE : HelpType.COMMAND_HELP,
    # One line summary of this help.
    HELP_ONE_LINE_SUMMARY : 'List providers, buckets, or objects',
    # The full help text.
    HELP_TEXT : _detailed_help_text,
  }

  def _PrintBucketInfo(self, bucket_uri, listing_style):
    """Print listing info for given bucket.

    Args:
      bucket_uri: StorageUri being listed.
      listing_style: ListingStyle enum describing type of output desired.

    Returns:
      Tuple (total objects, total bytes) in the bucket.
    """
    bucket_objs = 0
    bucket_bytes = 0
    if listing_style == ListingStyle.SHORT:
      print bucket_uri
    else:
      for obj in self.exp_handler.WildcardIterator(
          bucket_uri.clone_replace_name('**')).IterKeys():
        bucket_objs += 1
        bucket_bytes += obj.size
      if listing_style == ListingStyle.LONG:
        print '%s : %s objects, %s' % (
            bucket_uri, bucket_objs, MakeHumanReadable(bucket_bytes))
      else:  # listing_style == ListingStyle.LONG_LONG:
        location_constraint = bucket_uri.get_location(validate=False,
                                                      headers=self.headers)
        location_output = ''
        if location_constraint:
          location_output = '\n\tLocationConstraint: %s' % location_constraint
        self.proj_id_handler.FillInProjectHeaderIfNeeded(
            'get_acl', bucket_uri, self.headers)
        print '%s :\n\t%d objects, %s%s\n\tACL: %s\n\tDefault ACL: %s' % (
            bucket_uri, bucket_objs, MakeHumanReadable(bucket_bytes),
            location_output, bucket_uri.get_acl(False, self.headers),
            bucket_uri.get_def_acl(False, self.headers))
    return (bucket_objs, bucket_bytes)

  def _UriStrForObj(self, uri, obj):
    """Constructs a URI string for the given object.

    For example if we were iterating gs://*, obj could be an object in one
    of the user's buckets enumerated by the ls command.

    Args:
      uri: base StorageUri being iterated.
      obj: object (Key) being listed.

    Returns:
      URI string.
    """
    return '%s://%s/%s' % (uri.scheme, obj.bucket.name, obj.name)

  def _PrintInfoAboutBucketListingRef(self, bucket_listing_ref, listing_style):
    """Print listing info for given bucket_listing_ref.

    Args:
      bucket_listing_ref: BucketListing being listed.
      listing_style: ListingStyle enum describing type of output desired.

    Returns:
      Tuple (number of objects,
             object length, if listing_style is one of the long listing formats)

    Raises:
      Exception: if calling bug encountered.
    """
    uri = bucket_listing_ref.GetUri()
    obj = bucket_listing_ref.GetKey()
    if listing_style == ListingStyle.SHORT:
      print self._UriStrForObj(uri, obj).encode('utf-8')
      return (1, 0)
    elif listing_style == ListingStyle.LONG:
      # Exclude timestamp fractional secs (example: 2010-08-23T12:46:54.187Z).
      timestamp = obj.last_modified[:19].decode('utf8').encode('ascii')
      print '%10s  %s  %s' % (obj.size, timestamp,
                              self._UriStrForObj(uri, obj).encode('utf-8'))
      return (1, obj.size)
    elif listing_style == ListingStyle.LONG_LONG:
      # Run in a try/except clause so we can continue listings past
      # access-denied errors (which can happen because user may have READ
      # permission on object and thus see the bucket listing data, but lack
      # FULL_CONTROL over individual objects and thus not be able to read
      # their ACLs).
      try:
        uri_str = self._UriStrForObj(uri, obj)
        print '%s:' % uri_str.encode('utf-8')
        obj = self.suri_builder.StorageUri(uri_str).get_key(False)
        print '\tObject size:\t%s' % obj.size
        print '\tLast mod:\t%s' % obj.last_modified
        if obj.cache_control:
          print '\tCache control:\t%s' % obj.cache_control
        print '\tMIME type:\t%s' % obj.content_type
        if obj.content_disposition:
          print '\tContent-Disposition:\t%s' % obj.content_disposition
        if obj.content_encoding:
          print '\tContent-Encoding:\t%s' % obj.content_encoding
        if obj.content_language:
          print '\tContent-Language:\t%s' % obj.content_language
        if obj.metadata:
          for name in obj.metadata:
            print '\tMetadata:\t%s = %s' % (name, obj.metadata[name])
        print '\tEtag:\t%s' % obj.etag.strip('"\'')
        print '\tACL:\t%s' % (
            self.suri_builder.StorageUri(uri_str).get_acl(False, self.headers))
        return (1, obj.size)
      except boto.exception.GSResponseError as e:
        if e.status == 403:
          print('\tACCESS DENIED for reading ACL. Note: you need FULL_CONTROL'
                ' permission on each\n\tobject in order to read its ACL.')
          return (1, obj.size)
        else:
          raise e
    else:
      raise Exception('Unexpected ListingStyle(%s)' % listing_style)

  def _BuildBlrExpansionForUriOnlyBlr(self, blr):
    """
    Builds BucketListingRef expansion from BucketListingRef that contains only a
    URI (i.e., didn't come from a bucket listing). This case happens for BLR's
    instantiated from a user-provided URI.

    Args:
      blr: BucketListingRef to expand

    Returns:
      List of BucketListingRef to which it expands.
    """
    # Do a delimited wildcard expansion so we get any matches along with
    # whether they are keys or prefixes. That way if bucket contains a key
    # 'abcd' and another key 'abce/x.txt' the expansion will return two BLRs,
    # the first with HasKey()=True and the second with HasPrefix()=True.
    rstripped_blr = blr.GetRStrippedUriString()
    if ContainsWildcard(rstripped_blr):
      return list(self.exp_handler.WildcardIterator(rstripped_blr))
    # Build a wildcard to expand so CloudWildcardIterator will not just treat it
    # as a key and yield the result without doing a bucket listing.
    blr_expansion = list(
        self.exp_handler.WildcardIterator(rstripped_blr + '*'))
    # Find the originally specified blr in the expanded list (if present). Don't
    # just use the expanded list, since it would also include objects whose name
    # prefix matches the blr name (because of the wildcard match we did above).
    # Note that there can be multiple matches, for the case where there's
    # both an object and a subdirectory with the same name.
    exp_result = []
    for cur_blr in blr_expansion:
      if cur_blr.GetRStrippedUriString() == rstripped_blr:
        exp_result.append(cur_blr)
    return exp_result

  def _ExpandUriAndPrintInfo(self, uri, listing_style, should_recurse=False):
    """
    Expands wildcards and directories/buckets for uri as needed, and
    calls _PrintInfoAboutBucketListingRef() on each.

    Args:
      uri: StorageUri being listed.
      listing_style: ListingStyle enum describing type of output desired.
      should_recurse: bool indicator of whether to expand recursively.

    Returns:
      Tuple (number of matching objects, number of bytes across these objects).
    """
    # We do a two-level loop, with the outer loop iterating level-by-level from
    # blrs_to_expand, and the inner loop iterating the matches at the current
    # level, printing them, and adding any new subdirs that need expanding to
    # blrs_to_expand (to be picked up in the next outer loop iteration).
    blrs_to_expand = [BucketListingRef(uri)]
    num_objs = 0
    num_bytes = 0
    expanding_top_level = True
    printed_one = False
    num_expanded_blrs = 0
    while len(blrs_to_expand):
      if printed_one:
        print
      blr = blrs_to_expand.pop(0)
      if blr.HasKey():
        blr_expansion = [blr]
      elif blr.HasPrefix():
        # Bucket subdir from a previous iteration. Print "header" line only if
        # we're listing more than one subdir (or if it's a recursive listing),
        # to be consistent with the way UNIX ls works.
        if num_expanded_blrs > 1 or should_recurse:
          print '%s:' % blr.GetUriString().encode('utf-8')
          printed_one = True
        blr_expansion = list(self.exp_handler.WildcardIterator(
            '%s/*' % blr.GetRStrippedUriString()))
      elif blr.NamesBucket():
        blr_expansion = list(self.exp_handler.WildcardIterator(
            '%s*' % blr.GetUriString()))
      else:
        # This BLR didn't come from a bucket listing. This case happens for
        # BLR's instantiated from a user-provided URI.
        blr_expansion = self._BuildBlrExpansionForUriOnlyBlr(blr)
        num_expanded_blrs += len(blr_expansion)
        if num_expanded_blrs == 0 and not ContainsWildcard(uri):
          raise CommandException('No such object %s' % uri)
      for cur_blr in blr_expansion:
        if cur_blr.HasKey():
          # Object listing.
          (no, nb) = self._PrintInfoAboutBucketListingRef(
              cur_blr, listing_style)
          num_objs += no
          num_bytes += nb
          printed_one = True
        else:
          # Subdir listing. If we're at the top level of a bucket subdir
          # listing don't print the list here (corresponding to how UNIX ls
          # dir just prints its contents, not the name followed by its
          # contents).
          if (expanding_top_level and not uri.names_bucket()) or should_recurse:
            if cur_blr.GetUriString().endswith('//'):
	      # Expand gs://bucket// into gs://bucket//* so we don't infinite
	      # loop. This case happens when user has uploaded an object whose
              # name begins with a /.
              cur_blr = BucketListingRef(self.suri_builder.StorageUri(
                  '%s*' % cur_blr.GetUriString()), None, None, cur_blr.headers)
            blrs_to_expand.append(cur_blr)
          # Don't include the subdir name in the output if we're doing a
          # recursive listing, as it will be printed as 'subdir:' when we get
          # to the prefix expansion, the next iteration of the main loop.
          else:
            if listing_style == ListingStyle.LONG:
              print '%-33s%s' % ('', cur_blr.GetUriString().encode('utf-8'))
            else:
              print cur_blr.GetUriString().encode('utf-8')
      expanding_top_level = False
    return (num_objs, num_bytes)

  # Command entry point.
  def RunCommand(self):
    got_nomatch_errors = False
    listing_style = ListingStyle.SHORT
    get_bucket_info = False
    self.recursion_requested = False
    if self.sub_opts:
      for o, a in self.sub_opts:
        if o == '-b':
          get_bucket_info = True
        elif o == '-l':
          listing_style = ListingStyle.LONG
        elif o == '-L':
          listing_style = ListingStyle.LONG_LONG
        elif o == '-p':
          self.proj_id_handler.SetProjectId(a)
        elif o == '-r' or o == '-R':
          self.recursion_requested = True

    if not self.args:
      # default to listing all gs buckets
      self.args = ['gs://']

    total_objs = 0
    total_bytes = 0
    for uri_str in self.args:
      uri = self.suri_builder.StorageUri(uri_str)
      self.proj_id_handler.FillInProjectHeaderIfNeeded('ls', uri, self.headers)

      if uri.names_provider():
        # Provider URI: use bucket wildcard to list buckets.
        for uri in self.exp_handler.WildcardIterator(
            '%s://*' % uri.scheme).IterUris():
          (bucket_objs, bucket_bytes) = self._PrintBucketInfo(uri,
                                                              listing_style)
          total_bytes += bucket_bytes
          total_objs += bucket_objs
      elif uri.names_bucket():
        # Bucket URI -> list the object(s) in that bucket.
        if get_bucket_info:
          # ls -b bucket listing request: List info about bucket(s).
          for uri in self.exp_handler.WildcardIterator(uri).IterUris():
            (bucket_objs, bucket_bytes) = self._PrintBucketInfo(uri,
                                                                listing_style)
            total_bytes += bucket_bytes
            total_objs += bucket_objs
        else:
          # Not -b request: List objects in the bucket(s).
          (no, nb) = self._ExpandUriAndPrintInfo(uri, listing_style,
              should_recurse=self.recursion_requested)
          if no == 0 and ContainsWildcard(uri):
            got_nomatch_errors = True
          total_objs += no
          total_bytes += nb
      else:
        # URI names an object or object subdir -> list matching object(s) /
        # subdirs.
        (exp_objs, exp_bytes) = self._ExpandUriAndPrintInfo(uri, listing_style,
            should_recurse=self.recursion_requested)
        if exp_objs == 0 and ContainsWildcard(uri):
          got_nomatch_errors = True
        total_bytes += exp_bytes
        total_objs += exp_objs

    if total_objs and listing_style != ListingStyle.SHORT:
      print ('TOTAL: %d objects, %d bytes (%s)' %
             (total_objs, total_bytes, MakeHumanReadable(float(total_bytes))))
    if got_nomatch_errors:
      raise CommandException('One or more URIs matched no objects.')

  # test specification, see definition of test_steps in base class for
  # details on how to populate these fields
  test_steps = [
    # (test name, cmd line, ret code, (result_file, expect_file))
    ('gen bucket expect', 'echo gs://$B0/ >$F9', 0, None),
    ('gen obj expect', 'echo gs://$B1/$O0 >$F8', 0, None),
    ('simple ls', 'gsutil ls', 0, None),
    ('list empty bucket', 'gsutil ls gs://$B0', 0, None),
    ('list empty bucket w/ -b', 'gsutil ls -b gs://$B0 >$F7', 0,
                                                        ('$F7', '$F9')),
    ('list bucket contents', 'gsutil ls gs://$B1 >$F7', 0, ('$F7', '$F8')),
    ('list object', 'gsutil ls gs://$B1/$O0 >$F7', 0, ('$F7', '$F8')),
  ]
