r"""
Name : skinner.core.py
Author : Eric Pavey - warpcat@gmail.com - www.akeric.com
Creation Date : 2019-09-28
Description :
    Import/export skin weights.  It just works, fast.

    For the UI, see skinner.window.py

    Dependencies:
    * Python 3.x+
    * numpy & scipy on the path for import. To install them for
        your version of Maya, see the confirmDependencies function.

    Much learning around querying/setting skinCluster data via Maya API was found
    from these sources:
    https://gist.github.com/utatsuya/a95afe3c5523ab61e61b
    http://ueta.hateblo.jp/entry/2015/08/24/102937
    Other links:
    http://www.charactersetup.com/tutorial_skinWeights.html

To Do:
    * Weight Depot tab / functionality?
    * Provide option to save out as json?  change current format from .sknr to
       .sknrp (pickle) and make .sknrj for the json?  Something else like maybe
        _sknr.pkl (but that's Py2, Py3 seems to use .pickle) and _sknr.json ?
    * Update the SkinChunk.__init__ creation logic to store 'per-joint at bindpose'
        data, in addition to the mesh being at bindpose or not.

Updates:
    2021-09-26 : v1.0.0 : Ready for release.
    2021-10-01 : v1.0.1 : Updating getMeshVertIds to find all child mesh under
        the current selection.  Bugfix divideByZeroError in setWeights.  Bugfix
        in closestNeighborsWeights where -nan values were being set.  Updating
        exportSkinChunks to allow for version control integration.
    2021-10-07 : v1.0.2 : Bugfixing setWeights : it wasn't handling importing a
        subset of weights on a whole mesh: This is now fixed.  Added unlockInfluences
        and updated requiring code (setWeights, addInfluences).  Updating generateSkinChunks
        to have a progress bar.
    2021-10-08 : v1.0.3 : Bugfixing setWeights to use the corect value for skin
        smoothing.  Changing the setWeights arg postSmooth from a bool to an int.
    2021-10-18 : v1.0.4 : Bugfix to exportSkinChunks : Fixing pathing to use forwardslahes
        for version control call.
    2021-10-20 : v1.0.5 : Updating setWeights & importSkin to track skin weight
        import failures, and not crash the whole system if they happen.
    2021-10-22 : v1.0.6 : Adding SkinChunk.getByVertCountOrder and updating setWeights
        with new matchByVertCountOrder arg to make use of it.  Updating to allow
        for export / import on scenes with duplicate mesh names: Tracking stuff
        better by full path.  Bugfixing how skin smoothing works, which was causing
        smoothed mesh to deform poorly.
    2021-10-23 : v1.0.7 : Refactor many internal functions into the utils.py module.
    2021-10-25 : v1.0.8 : Updating importSkin to have new printOverviewMode arg.
        Updating generateSkinChunks & setToBindPose + calling code with setToBindPose arg.
    2021-11-05 : v1.0.10 : Updating to remove calls to the scripted plugin based
        on a new soltuion that runs faster without it.
    2021-11-08 : v1.0.12 : Bugfixing SkinChunk.__init__ to better handle duplicate
        names in the scene.  Bugfixing setWeights to handle mesh and joints with
        the same names.
    2021-11-10 :  1.0.13 : Working around Maya bug in setWeights where hidden mesh
        shape nodes will fail to have new skinCluster nodes generated for them.
    2021-12-02 : v1.0.14 : Updating generateSkinChunks & setWeights to detect for
        incompatible normalizeWeights values, and offer to auto-correct.
    2021-12-03 : v1.0.15 : Updating core.setWeights to update the return to include
        any new influences created.  Updating exportSkin, exportTempSkin, and
        importTempSkin to all have consistent 'item' parameters/args with importSkin.
    2021-12-07 : v1.0.16 : Adding version info to SkinChunks. Small bugfix to
        SkinChunk.printData for numVerts.
    2021-12-13  :v1.0.17 : Updating generateSkinChunks to handle buggy imported
        FBX data that was setting skinCluster.skinningMethod to -1 (invalid).
    2021-12-15 : v1.1.0 : New feature to also query/store worldspace positions during
        export based on the pre-deformed (aka intermediateObject) shape node, in
        addition to the post-deformed one.  Updating SkinChunk, generateSkinChunks,
        and exportSkin to support this.  In the process set many args that were
        setToBindPose=True to False.  Bugfix to setWeights undoqueue, that was
        applying bad weights when only a subset should be imported on.  Bugfix
        to 'double not' statement at the bottom of this module.  Not sure how
        that slipped in...  Provide more examples below.
    2021-12-19 : v1.1.1 : Updating SkinChunks to store local transformations and
        rotateOrder values on joints.  Bugfixing setWeights to properly set influences
        to bindpose on mesh that didn't yet have skinning, based on the influences
        stored in the SkinChunk data.  SkinChunks now track if they weren't at the
        bindpose when created.
    2021-12-30 : v1.1.2 : Updating all source to use Python3 type hint notation.
    2022-01-06 : v1.1.4 : Updating setWeights skinCluster smoothing code with a
        fixed tolerance value.
    2022-03-09 : v1.1.7 : Updating setWeights with new postSmoothWeightDiff arg.
       Changing the default post smooth diff value from .01 to .25, to help resolve
       odd skinning bugs.
    2022-03-31 : v1.1.8 : Bugfixing string formatting error in setWeights.
    2022-05-18 : v1.1.9 : Updating closestPointKdTree to allow numNeighbors=1.
        Before that it would be auto-set to 2, based on my not understanding how
        the ndarray return values worked.  Also updating it to support older versions
        of KDTree that don't have the 'workers' arg.
    2024-06-04 : v1.1.11 : Bugfixing tool to properly paste weights on selected
        verts.  Specifically updating setWeights to leverage the new utils.transposeWeights
        to sort SkinChunk weights in the same order as the influences on the skinCluster.
        Also raising more expections if 'selectVertsOnly' is set and operations
        would happen that would change the skinning.  Various verbose logging formatting
        changes.
    2024-06-10 : v1.2.0 : Setting setWeights's unskinFirst arg default to False,
        was True. Adding regenrateSkinCluster.  Adding new tempFilePath arg, and
        kwargs capturing to both exportTempSkin and importTempSkin.  Updating
        the undoChunk closing code with specific names.

Examples:

For all below:
import skinner.core as skinCore

#-----------
# Run the test suite.  This will prompt the user to continue via a dialog since
# it is destructive to the scene (creates a new one).
skinCore.test()

#-----------
# Export and import temp weights on selection

# Select mesh/components etc and :
skinCore.exportTempSkin()
# Select other mesh/components etc and:
skinCore.importTempSkin()

#-----------
# Export / import skin weights on a defined lists of mesh/components to a given file.

filePath = "C:/path/to/some/skinner/file.sknr"

# Export the items to the file:
exportItems = [list of mesh and component names]
exportResults = skinCore.exportSkin(items=exportItems, filePath=filePath)

# Import onto other items.  note the filePaths arg can take a single string, or
# a list of paths:
importItems = [list of mesh and component names]
importResults = skinCore.importSkin(items=importItems, filePaths=filePath)

"""
import os
import sys
import time
import pickle
import itertools
import tempfile
import traceback
from datetime import datetime
from collections import OrderedDict

import maya.cmds as mc
import maya.api.OpenMaya as om2

# See notes above for install
try:
    import numpy as np
except ImportError:
    np = None
try:
    from scipy.spatial import KDTree
except ImportError:
    KDTree = None

from . import utils
from . import __version__

#---------------------------

# Same list indexed values values as the skinCluster.skinningMethod enum
SKIN_METHODS = ("classic linear", "dual quaternion", "weight blended")

EXT = "sknr"
TEMP_DIR = os.path.join(tempfile.gettempdir(), "skinner")
TEMP_FILE = f"temp.{EXT}"
TEMP_FILE_PATH = os.path.join(TEMP_DIR, TEMP_FILE)
TEMP_FILE_REGEN = f"temp_regen.{EXT}"

# Maya optionVar settings
OV_LAST_SAVE_PATH = "ov_skinner__lastSavePath"

# Used as a default arg in closestPointKdTree to set multithreading in KDTree.query()
gMultiThread = True

#---------------------------------
# Utils

def printWeightFile(filePath:str, importVerbose=False, **kwargs):
    r"""
    Print data in the provided weight file path.

    Parameters:
    filePath : string : The full path to the weight file to print.
    importVerbose : bool : Default False : Should the import process also print info?
    kwargs : keyword arguments to pass directly to the SkinChunk.printData method.
    """
    skinChunks = importSkinChunks(filePath, verbose=importVerbose)
    print("SkinChunk Data for : %s"%filePath)
    for skinChunk in skinChunks:
        skinChunk.printData(**kwargs)

#-------------------------------------------------------------------------------
# Closest Point Algorithms

def closestPointExample(points:np.ndarray, targets:np.ndarray, numNeighbors:int) -> tuple:
    r"""
    This is an example of writing your own closest point wrapper function: Follow
    the signature of the parameters/arguments/return.

    Parameters
    points : ndarray[n][3] : The 3D points we're querying for.  Aka, the 'verts
        getting weights loaded on them', in that vert ID order.
    targets : ndarray[n][3] : All the 3D points being tested against: Their
        order represents the vert index order.  They'er what the kdTree is being
        made on.
    numNeighbors : int : The number of closest neighbors to find/return.

    Return : tuple : both are ndarrays of the same length in the vert order of the
        passed in points array.
        distances : ndarray[x][y] where x is the length of the points arg, and y
            is the numNeighbors arg.  These are the closest target distances in
            order, from closest to furthest, based on the target point indexes
            array, next:
        indexes : ndarray[x][y] where x is the length of the points arg, and y
            is the numNeighbors arg.  These are the closest target indices in
            order, from closest to furthest, based on the corresponding distances
            array, above.
    """
    raise NotImplementedError()

def closestPointKdTree(points:np.ndarray, targets:np.ndarray, numNeighbors:int) -> tuple:
    r"""
    Find the closest point(s) based on the scipy.spatial.KDTree algorithm
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.KDTree.html
    Very fast!

    This also uses the global gMultiThread to determine if it should use all threads
    for the compute.

    Parameters
    points : ndarray[n][3] : The 3D points we're querying for.  Aka, the 'verts
        getting weights loaded on them', in that vert ID order.
    targets : ndarray[n][3] : All the 3D points being tested against: Their
        order represents the vert index order.  They're what the kdTree is being
        made on;  What originally had weights saved on them.
    numNeighbors : int : The number of closest neighbors to find/return.

    Return : tuple : both are ndarrays of the same length in the vert order of the
        passed in points array.  It is the direct return from KDTree.query()
        distances : ndarray[x][y] where x is the length of the points arg, and y
            is the size of numNeighbors arg.  These are the closest target distances
            in order, from closest to furthest, based on the target point indexes
            array, next:
        indexes : ndarray[x][y] where x is the length of the points arg, and y
            is the size of numNeighbors arg.  These are the closest target indices
            in order, from closest to furthest, based on the corresponding distances
            array, above.
    """
    global gMultiThread
    if not KDTree:
        raise ImportError("Unable to import the scipy.spatial module to access the KDTree class")
    if len(targets) < numNeighbors:
        numNeighbors = len(targets)

    workers = 1 # The KDTree.query default : Use 1 processor.
    if gMultiThread:
        workers = -1 # use all'dem
    # Build and query a kdTree for our target points, then return the results
    # checking them against our sample points:
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.KDTree.query.html#scipy.spatial.KDTree.query
    try:
        distances, indexes = KDTree(targets).query(points, numNeighbors, workers=workers)
    except:
        # Older versions of KDTree don't support the workers arg.
        distances, indexes = KDTree(targets).query(points, numNeighbors)

    if numNeighbors == 1:
        # If we only query one closest distance, numpy will return an array of scalars,
        # not an array of arrays.  For consistency, we want it to always return
        # an array of arrays.
        distances = [[item] for item in distances]
        indexes = [[item] for item in indexes]
    return (distances, indexes)

def closestPointBruteForce(points:np.ndarray, targets:np.ndarray, numNeighbors:int) -> tuple:
    r"""
    Find closest point by brute force.  The more the targets, the slower it gets.
    Can use this to compare your wiz-bang algorithms against, and feel better
    about yourself.

    Parameters
    points : ndarray[n][3] : The 3D points we're querying for.  Aka, the 'verts
        getting weights loaded on them', in that vert ID order.
    targets : ndarray[n][3] : All the 3D points being tested against: Their
        order represents the vert index order.  They'er what the kdTree is being
        made on.
    numNeighbors : int : The number of closest neighbors to find/return.

    Return : tuple : both are ndarrays of the same length in the vert order of the
        passed in points array.
        distances : ndarray[x][y] where x is the length of the points arg, and y
            is the numNeighbors arg.  These are the closest target distances in
            order, from closest to furthest, based on the target point indexes
            array, next:
        indexes : ndarray[x][y] where x is the length of the points arg, and y
            is the numNeighbors arg.  These are the closest target indices in
            order, from closest to furthest, based on the corresponding distances
            array, above.
    """
    distances = []
    indexes = []
    if len(targets) < numNeighbors:
        numNeighbors = len(targets)

    for i,point in enumerate(points):
        distIndices = []
        for j, targPoint in enumerate(targets):
            dist = np.linalg.norm(point-targPoint)
            distIndices.append([dist, j])
        distIndices = sorted(distIndices)
        trim = numNeighbors
        if len(distIndices) < trim:
            trim = len(distIndices)
        theseDist = []
        theseIndexes = []
        for k in range(trim):
            theseDist.append(distIndices[k][0])
            theseIndexes.append(distIndices[k][1])
        distances.append(theseDist)
        indexes.append(theseIndexes)

    return np.array(distances), np.array(indexes)

#-------------------------------------------------------------------------------
# Weighting Algorithms

def closestNeighborsWeights(allSavedWeights:np.ndarray, allSavedBlendWeights:np.ndarray,
                            importVertPositions:np.ndarray, savedVertPositions:np.ndarray,
                            importVertNormals:list, savedVertNormals:list,
                            closestNeighborCount:int, closestNeighborDistMult:float,
                            closestPointFunc=closestPointKdTree,
                            filterByVertNormal=False, vertNormalTolerance=0.0) -> dict:
    r"""
    The algorithm used to cacluate new weights (and blendWeights) based on the
    "closest neighbor's weights (or blendWeights)" to each target vert.

    The "one sentence description" is:
    "Look for target verts/points around the source vert/point based on a distance
    tolerance, and based on those distances, calculate new weights linearly prioritizing
    the weights closest to the source."

    Example for weights.  BlendWeights are slightly more simplistic since it's a
    single value per vert, rather than an array of values per influence per vert,
    for regular weights.
    A : For each target vert position in the importVertPositions...
    B : Find the closest neighbor points to it in savedVertPositions, based on the
        closestNeighborCount (say, 3), in a 'vert pool'.
    C : From that pool, find the closest point (item 0) to the target vert: Store
        that distance.  Say, it is 1 unit.
    D : Based on the other verts in the  pool, see if they  within the
        'closestNeighborDistMult * the closest distance': If they are
        outside that distance, remove them from vert pool.  For example, if
        closestNeighborDistMult was 2, and  'the distance to the cloest vert' was
        1.0, then it will search 2.0 units (1.0 * 2.0) around the target vert in
        the vert pool for others that fall within that radius.
    E : For that  pool of verts, based on their distances,
        calculate their 'normalized distances'.  For example, if the distances
        from the target verts were 1.0, 1.5, and 2.0 units, the corresponding normalized
        distances are  [0.22, 0.33, 0.44]. But that deprioritizes the closer weights,
        so that is reversed to become: [0.44 0.33, 0.22].
    F : Then for each of the influences affecting each of the verts in the pool,
        an uber-list of weights is generated of those influece weights, each weight
        being multiplied by corresponding normalized weight above, to prioritize
        weights of influences closer to the target, and deprioritize weights further
        from the target, based on the normalized distances.
    G : That weight list is returned, for application to the skinCluster.
    H : So in a nutshell, look for verts around the target, and based on
        those distances, calculate new weights linearly prioritizing the weights
        closest to the target.

    Parameters:
    allSavedWeights : ndarray[x][y] (weights)  : The weights that were previously
        saved, and now being loaded.
        Ultimately this is the return from either UberChunk.getAllWeights() /
        SkinChunk.getAllWeights().
    allSavedBlendWeights : ndarray[x] : The 'blend weights' (if the skinCluster
        type being imported on is 'weight blended') that were previously saved,
        and now being loaded.
        Ultimately this is the return from either
        UberChunk.getAllBlendWeights() / SkinChunk.getAllBlendWeights().  While
        somethiing must be provided, this can be an empty array to skip the compute.
        If it is provided, it must be the same length as allSavedWeights.
    importVertPositions : ndarray[n][3] : The 3d sample points for each worldspace
        location for each source vert having weights applied to.  The 'source points'.
    savedVertPositions : ndarray[n][3] : The 3d space sample points in the
        SkinChunk or UberChunk being sampled/loaded.  The 'target points'.
    importVertNormals : list : om2.MVector representation of the vert normal for
        each vert having weights imported.  Needs to be the same number as savedVertPositions.
    savedVertNormals : list : om2.MVector representation of the vert normal for
        each vert having weights loaded from, as loaded from a SkinChunk or UberChunk.
    closestNeighborCount : int : How many target verts should be sampled to generate
        the new weight influences.  This is the max value, only verts found within
        'closest first distance * closestNeighborDistMult' will be considered.
        Values of 3-6 are standard. If this value is 0 or -1, or if filterByVertNormal
        is used, it will be set to the total number of verts being imported on,
        aka, len(savedVertPositions).
    closestNeighborDistMult : float : This defines the 'search bubble distance'
        when looking for other close target verts:  If the closest target vert is
        1 unit away, the tools will search with a radius of 1 unit * closestNeighborDistMult
        for other target positions\influences.  2.0 is standard.
    closestPointFunc : function/None : Default closestPointKdTree : If None, use
        closestPointBruteForce : The 'closest point function' to use.  Broken out
        as an arg so you can pass in your own, if you got something faster than
        what this tool uses.  See the docstring of closestPointExample if you want
        to roll your own.
    filterByVertNormal : bool : Default False : If True, use the vertNormalTolerance
        value to filter out verts that have opposing normals, to reduce grabbing
        weights from mesh they shouldn't.
    vertNormalTolerance : float : Default 0.0 : This is the dot product tolerance
        used to determine if a vert/weight should be included in the algorithm:
        If the source vert (the one getting skinning applied) and the target verts
        (one with the saved weights) normals (vectors) both point the same direction,
        the dot is 1.0.  If the target is 90 deg off from the source, the dot is
        0.0.  If the target is 180 deg off from the source, the dot is -1 : Any
        dot found less than this tolerance will be rejected.

    Return : dict : key:values for:
        *  "weights": each item is a sublist of influence weights, per source vert.
        *  "blendWeights" : A single list of floats, presuming allSavedBlendWeights
            was passed in.
    """
    if importVertNormals:
        assert len(importVertNormals) == len(importVertPositions), f"The number of 'import vert positions ({len(importVertPositions)}) doesn't match the number of import vert normals ({len(importVertNormals)})"
    if filterByVertNormal and not importVertNormals:
        raise Exception("importByVertNormal=True, but importVertNormals is empty.")

    useBlendWeights = False
    if isinstance(allSavedBlendWeights, type(np.array)):
        assert len(allSavedWeights) == len(allSavedBlendWeights), "allSavedBlendWeights was provided, but its length (%s) is not equal to allSavedWeights (%s)"%(len(allSavedBlendWeights), len(allSavedWeights))
        useBlendWeights = True

    if closestPointFunc is None:
        closestPointFunc = closestPointBruteForce

    # Python list, since numpy can't append to arrays
    newWeights = []
    newBlendWeights = []

    if closestNeighborCount < 1:
        # use everything found.
        closestNeighborCount = len(importVertPositions)

    # If we're filtering by vert normals, we need to possilby compare against a
    # lot more verts in the pool.
    closestNeighborCountOverride = closestNeighborCount
    if filterByVertNormal:
        closestNeighborCountOverride = len(importVertNormals)

    # Find the closest points including things that should be filtered out by our
    # normal filter below.
    #
    # distancesArr[i][j] : For every pos [i] in importVertPositions, this is a
    # ordered list of all the closest savedVertPoints [j]
    #
    # indexArr[i][j] : for every pos [i] in importVertPositions, this is the corresponding
    # ordered index for the distances in distancesArr [j].
    #
    # So, the closest distance to importVertPositions[i] is distancesArr[i][0]
    # The second closest distance to importVertPositions[i] is distancesArr[i][1]
    # And, the closest index to importVertPositions[i] is indexArr[i][0]
    # The second closest index to importVertPositions[i] is indexArr[i][1]
    # etc.
    distancesArr, indexArr = closestPointFunc(importVertPositions, savedVertPositions,
                                              numNeighbors=closestNeighborCountOverride)

    #for i,importVertPos in enumerate(importVertPositions):
    for i in range(len(importVertPositions)):
        # Start building our data:  Since numpy can't append to arrays, we'll
        # use Python lists here:
        closestDistances = []
        closestIndices = []
        rejectedDistnaces = []
        rejectedIndices = []
        searchDist = distancesArr[i][0] * closestNeighborDistMult

        for j in range(0, len(distancesArr[i])):
            if len(closestIndices) >= closestNeighborCount:
                break
            checkIndex = indexArr[i][j]
            checkDist = distancesArr[i][j]
            if checkDist > searchDist and not filterByVertNormal:
                break

            normalReject = False
            if filterByVertNormal:
                dot = importVertNormals[i] * savedVertNormals[checkIndex]
                # Compare the normal of this vert to the normal of the check vert,
                # via the dot product:
                if dot < vertNormalTolerance:
                    normalReject = True

            if not normalReject:
                closestIndices.append(checkIndex)
                closestDistances.append(checkDist)
            else:
                rejectedIndices.append(checkIndex)
                rejectedDistnaces.append(checkDist)

        if not closestIndices and filterByVertNormal:
            # We didn't find anything, based on our vert normal filter, so in this
            # case, just use the rejected list.
            maxIndex = min([closestNeighborCount, len(rejectedIndices)])
            closestIndices = rejectedIndices[:maxIndex]
            closestDistances = rejectedIndices[:maxIndex]

        # We how have (up to) the (closestNeighborCount) closest indices, process
        # what the weights should be.
        numCloseIndices = len(closestIndices)
        if numCloseIndices == 1:
            # No magic or extra maths, just closest point, since only one point
            # is close enough to sample based on our input arguments:
            newWeights.append(allSavedWeights[int(closestIndices[0])])
            if useBlendWeights:
                newBlendWeights.append(allSavedBlendWeights[int(closestIndices[0])])

        else:
            # Teh Algorithzms

            # Figure out how close this pos is to the closestIndex[i] pos
            # Normalize that distance vs the closest.
            # Then, based on that normalization, figure out all
            # the weights for all the influences of each pos index,
            # And write those weights out.

            # If we passed in weights, each item is a sublist of weights for the closest indices
            # If we passed in weightList, its a single list.
            closesetIndexWeights = [allSavedWeights[int(index)] for index in closestIndices]

            # Have hit bugs where closestDistances is a list of all zeroes. If so,
            # average it all
            if not any(closestDistances):
                avg = 1.0 / len(closestDistances)
                closestDistances = [avg for i in range(len(closestDistances))]

            # Make all distances fit between 0->1.0
            # CAN SET NAN if closestDistances is all zero
            normalizedDistances = utils.normalizeToOne(closestDistances)

            # However, this deprioritizes the weights of things closer, so
            # we need to revere the results.
            normalizedDistances.reverse()

            # Handling weights : allSavedWeights is ndarray[x][y]
            # Adjust the weights based on their proximity to the point.
            # If we passed in weights, this is a list of sublists of weights: Each
            # row is some point  in space, and each column reflects an influence value.
            weightByDist = []
            for weightListIndex,weightList in enumerate(closesetIndexWeights):
                wbd = [weight*normalizedDistances[weightListIndex] for weight in weightList]
                weightByDist.append( wbd )

            # Add up all the weights by row (axis0), across our multiple
            # columns of weightLsits, so we have a single list
            # of the weights per influence, but non-normalized:
            sumedWeights = np.sum(weightByDist, axis=0)

            # And finally normalize these weights between zero and one:
            normalizedWeights = utils.normalizeToOne(sumedWeights)
            newWeights.append(normalizedWeights)

            if useBlendWeights:
                # Handling blendWeights : allSavedBlendWeights is ndarray[x]
                # Adjust the weights based on their proximity to the point.
                # If we passed in blendWeights, this is a single list of values.
                weightByDist = []
                for weightListIndex,weight in enumerate(closesetIndexWeights):
                    weightByDist.append( weight*normalizedDistances[weightListIndex]  )
                # Add up the values of the normalized distances:
                sumedWeights = np.sum(weightByDist, axis=0)
                newBlendWeights.append(sumedWeights)

    return {"weights":newWeights, "blendWeights":newBlendWeights}

def closestPointWeights(allSavedWeights:np.ndarray, allSavedBlendWeights:np.ndarray,
                        importVertPositions:np.ndarray, savedVertPositions:np.ndarray,
                        importVertNormals:list, savedVertNormals:list,
                        closestPointFunc=closestPointKdTree,
                        filterByVertNormal=False, vertNormalTolerance=0.0):
    r"""
    The 'closest point' algorithm used to find the weight/influences of the closest
    target to each source.  Pretty straight forward.

    Parameters:
    allSavedWeights : ndarray[x][y] (weights)  : The weights that were previously
        saved, and now being loaded.
        Ultimately this is the return from either UberChunk.getAllWeights() /
        SkinChunk.getAllWeights().
    allSavedBlendWeights : ndarray[x] : The 'blend weights' (if the skinCluster
        type being imported on is 'weight blended') that were previously saved,
        and now being loaded.
        Ultimately this is the return from either
        UberChunk.getAllBlendWeights() / SkinChunk.getAllBlendWeights().  While
        somethiing must be provided, this can be an empty array to skip the compute.
        If it is provided, it must be the same length as allSavedWeights.
    importVertPositions : ndarray[n][3] : The 3d sample points for each worldspace
        location for each source vert having weights applied to.  The 'source points'.
    savedVertPositions : ndarray[n][3] : The 3d space sample points in the
        SkinChunk or UberChunk being sampled/loaded.  The 'target points'.
    importVertNormals : list : om2.MVector representation of the vert normal for
        each vert having weights imported.  Needs to be the same number as savedVertPositions.
    savedVertNormals : list : om2.MVector representation of the vert normal for
        each vert having weights loaded from, as loaded from a SkinChunk or UberChunk.
    closestPointFunc : function/None : Default closestPointKdTree : If None, use
        closestPointBruteForce : The 'closest point function' to use.  Broken out
        as an arg so you can pass in your own, if you got something faster than
        what this tool uses.  See the docstring of closestPointExample if you want
        to roll your own.
    filterByVertNormal : bool : Default False : If True, use the vertNormalTolerance
        value to filter out verts that have opposing normals, to reduce grabbing
        weights from mesh they shouldn't.
    vertNormalTolerance : float : Default 0.0 : This is the dot product tolerance
        used to determine if a vert/weight should be included in the algorithm:
        If the source vert (the one getting skinning applied) and the target verts
        (one with the saved weights) normals (vectors) both point the same direction,
        the dot is 1.0.  If the target is 90 deg off from the source, the dot is
        0.0.  If the target is 180 deg off from the source, the dot is -1 : Any
        dot found less than this tolerance will be rejected.

    Return : dict : key:values for:
        *  "weights": each item is a sublist of influence weights, per source vert.
        *  "blendWeights" : A single list of floats, presuming allSavedBlendWeights
            was passed in.

    Return : dict : key:values for:
        *  "weights": each item is a sublist of influence weights, per source vert.
        *  "blendWeights" : A single list of floats, presuming allSavedBlendWeights
            was passed in.
    """
    if importVertNormals:
        assert len(importVertNormals) == len(importVertPositions), f"The number of 'import vert positions ({len(importVertPositions)}) doesn't match the number of import vert normals ({len(importVertNormals)})"
    if filterByVertNormal and not importVertNormals:
        raise Exception("importByVertNormal=True, but importVertNormals is empty.")

    useBlendWeights = False
    if isinstance(allSavedBlendWeights, type(np.array)):
        assert len(allSavedWeights) == len(allSavedBlendWeights), "allSavedBlendWeights was provided, but its length (%s) is not equal to allSavedWeights (%s)"%(len(allSavedBlendWeights), len(allSavedWeights))
        useBlendWeights = True

    if closestPointFunc is None:
        closestPointFunc = closestPointBruteForce
    newWeights = []
    newBlendWeights = []

    # Calculate our closest point data:
    numNeighbors = 1
    if filterByVertNormal:
        numNeighbors = len(importVertPositions)

    # Find the closest points including things that should be filtered out by our
    # normal filter below.
    #
    # distancesArr[i][j] : For every pos [i] in importVertPositions, this is a
    # ordered list of all the closest savedVertPoints [j]
    #
    # indexArr[i][j] : for every pos [i] in importVertPositions, this is the corresponding
    # ordered index for the distances in distancesArr [j].
    #
    # So, the closest distance to importVertPositions[i] is distancesArr[i][0]
    # The second closest distance to importVertPositions[i] is distancesArr[i][1]
    # And, the closest index to importVertPositions[i] is indexArr[i][0]
    # The second closest index to importVertPositions[i] is indexArr[i][1]
    # etc.
    distancesArr, indexArr = closestPointFunc(importVertPositions, savedVertPositions, numNeighbors=numNeighbors)

    for i in range(len(importVertPositions)):
        closestIndex = indexArr[i][0]


        if filterByVertNormal:
            closestNormalMatch = None
            for j in range(0, len(distancesArr[i])):
                checkIndex = indexArr[i][j]
                dot = importVertNormals[i] * savedVertNormals[checkIndex]
                # Compare the normal of this vert to the normal of the check vert,
                # via the dot product:
                if dot >= vertNormalTolerance:
                    closestNormalMatch = indexArr[i][j]
                    break
            if closestNormalMatch:
                closestIndex = closestNormalMatch
            # if we don't find a closestNormalMatch based on any avilable normal
            # just default to the closest point defined above.

        newWeights.append(allSavedWeights[int(closestIndex)])
        #print(i, closestIndex, allSavedWeights[int(closestIndex)])

        if useBlendWeights:
            newBlendWeights.append(allSavedBlendWeights[int(closestIndex)])

    return {"weights":newWeights, "blendWeights":newBlendWeights}

#-----------------------------
# Our Chunks, behold them!

class Chunk:
    r"""
    Chunk is the superclass that SkinChunks and UberChunks are based on: It contains
    the superset of methods they both share, to reduce code redundancy/complexity.
    """

    def __init__(self):
        r"""
        Initialize our Chunk instance with empty values.
        """
        self.totalMeshVerts = 0
        self.influences = []
        self.influenceMatrices = []
        self.influenceLocalTransforms = [] # Added 1.1.1
        self.influenceRotateOrders = [] # Added 1.1.1
        self.influenceParents = []
        self.weights = []
        self.blendWeights = []
        self.normals = []
        self.normalsPreDeformed = [] # Added 1.1.0
        self.vertPositions = []
        self.vertPositionsPreDeformed = [] # Added 1.1.0

    #------------
    # Queries

    def hasInfluence(self, influence:str) -> bool:
        r"""
        Return True/False  if the provided influence leaf string name is part of
        this Chunk.
        """
        inf = influence.split("|")[-1].split(":")[-1]
        if inf in self.influences:
            return True
        else:
            return False


    def getAllWeights(self) -> np.ndarray:
        r"""
        Return a ndarray[x][y] where Each item (x, represents vert ids) is a
            sublist (y)  : The sublist are weights in relationship to the passed
            ininfluences list.  Ultimately, this was generated by utils.getWeights.
        """
        return self.weights

    def getAllBlendWeights(self) -> np.ndarray:
        r"""
        Return a ndarray[x] where Each item (x) is a corresponding 'blendWeight'
            to the same index in vertIds : Ultimately, this was generated by
            utils.getBlendWeights.
        """
        return self.blendWeights

    def getAllNormals(self, preDeformed=False) -> np.ndarray:
        r"""
        Return a ndarray[x][y] for the worldspace vert normals.  Ultimately, this
        is generated by utils.getVertNormals.

        Parameters:
        preDeformed : bool : Added in 1.1.0 : If this is False,
            return the worldspace normals for the verts when the SkinCluster was
            generated.  If True, return the 'pre-deformed' normals that were stored
            out.
        """
        # Introduced in 1.1.0 :
        if preDeformed and hasattr(self, "normalsPreDeformed"):
            return self.normalsPreDeformed
        else:
            return self.normals

    def getInfluences(self) -> list:
        r"""
        Return a list of string leaf names of the influences in this Chunk.
        """
        return self.influences

    def getInfluenceMatrices(self) -> list:
        r"""
        Return a list, where each item is the worldspace matrix (as a list of 16
        floats) for each influence saved int his Chunk.
        """
        return self.influenceMatrices

    def getInfluenceLocalTransforms(self) -> list:
        r"""
        New in 1.1.1
        Return a list, where each item represents an influence in this Chunk.
        Each value is a dict, with keys for "translate", "rotate", "scale", "rotateAxis",
        "jointOrient", an values the corresponding [x,y,z] values
        """
        try:
            return self.influenceLocalTransforms
        except AttributeError:
            return {}

    def getInfluenceRotateOrders(self) -> list:
        """
        New in 1.1.1
        Return a list, where each item represents the (int) rotateOrder for that
        influence in this Chunk
        """
        try:
            return self.influenceRotateOrders
        except AttributeError:
            return 0 # xyz

    def getInfluenceParents(self) -> list:
        r"""
        Return a list of leaf string names for the parent of each influence saved
        in this Chunk.
        """
        return self.influenceParents

    def getVertPositions(self, preDeformed=False) -> list:
        r"""
        Based on the saved vert IDs, return back a list of their worldspace positions,
        as sublists of 3 floats, based on what's saved in this Chunk.

        Parameters:
        * preDeformed : bool : Default = False : New in 1.1.0 : If this is False,
            return the worldspace positions for the verts when the SkinCluster was
            generated.  If True, return the 'pre-deformed' positions that were stored
            out.

        Return : list : The positions of the verts.
        """
        # Introduced in 1.1.0 :
        if preDeformed and hasattr(self, "vertPositionsPreDeformed"):
            return self.vertPositionsPreDeformed
        else:
            return self.vertPositions

    #------------
    # Actions

    def buildMissingInfluences(self) -> dict:
        r"""
        Build (create & position in worldspace via the stored matrix data) any
        missing influences (joints) based on what's been saved in this Chunk.
        Also try and parent them to their original parent if it exists as well.
        Since the new joints are positioned by passing a worldspace matrix to the
        xform command, while they will have the correct worldspace orientation/
        position as what was orignially saved, their local rotation / jointOrient
        values could be different, especially if what they get parented to is in a
        different location in worldspace than the scene this was generated in.

        A missing influence will always be created.  It will parent itself to a
        parent if: That parent can be found, and only a single instance by that
        leaf name exists.

        It searches for both influence joint names, and the parents, by leaf
        names and no namespaces.

        In the return dict, if the values for both missingParents and dupeParentNames
        are empty, then you know everything worked correctly.

        Return : dict : k:v pairs for:
            "newInfluences" : list : The leaf names of the new influence joints
                created.
            "missingParents" : list : Each item is a sublist of:
                [ "newInfluence", "missingParent" ]
            "dupeParentNames" : list : Each item is a sublist of:
                [ "newInfluence", [list, of, duplicate, parent, joint, names] ]
            "goodParenting" : list : Each item is a sublist of:
                [ "newInfluence", "whatItIsParentedTo" ]
        r"""
        influences = self.getInfluences()
        infMatrices = self.getInfluenceMatrices()
        infLocalTransforms = self.getInfluenceLocalTransforms() # new 1.1.1
        infRotateOrders = self.getInfluenceRotateOrders() # new 1.1.1
        infParents = self.getInfluenceParents()

        # Build & Position Influences in worldspace first.
        newInfs = []
        newInfParents = []
        for i,inf in enumerate(influences):
            exists = mc.ls(inf)
            if not exists:
                mc.select(clear=True)
                newInf = mc.joint(name=inf)
                newInfs.append(newInf)
                mc.setAttr(f"{newInf}.rotateOrder", infRotateOrders[i])
                mc.xform(newInf, matrix=infMatrices[i], worldSpace=True)
                newInfParents.append(infParents[i])

        # Parent Influences (since some of these parents may have been influences
        # created in the above step)
        missingParents = []
        dupeParentNames = []
        goodParenting = []
        for i,newInf in enumerate(newInfs):
            localTransformData = infLocalTransforms[i]
            if newInfParents[i] == None:
                # It's parent is the world.
                goodParenting.append([newInf, "The World"])
                if localTransformData: # Could be empty if old data before this feature was around
                    currentMtx = mc.xform(newInf, query=True, matrix=True, worldSpace=True)
                    for attr in localTransformData:
                        mc.setAttr(f"{newInf}.{attr}", *localTransformData[attr], type="double3")
                    updateMtx = mc.xform(newInf, query=True, matrix=True, worldSpace=True)
                    if updateMtx != currentMtx:
                        # Too bad, let's put it back:
                        mc.xform(newInf, matrix=currentMtx, worldSpace=True)
                continue
            parentExists = mc.ls(newInfParents[i])
            if not parentExists:
                missingParents.append([newInf, newInfParents[i]])
                continue
            if len(parentExists) > 1:
                dupeParentNames.append(newInf, parentExists)
                continue
            newInfName = mc.parent(newInf, parentExists[0])[0]
            goodParenting.append([newInf, parentExists[0]])

            # Now that it's been parented correctly, let's see if the local transforms
            # work:
            if localTransformData: # Could be empty if old data before this feature was around
                currentMtx = mc.xform(newInfName, query=True, matrix=True, worldSpace=True)
                for attr in localTransformData:
                    mc.setAttr(f"{newInfName}.{attr}", *localTransformData[attr], type="double3")
                updateMtx = mc.xform(newInfName, query=True, matrix=True, worldSpace=True)
                if updateMtx != currentMtx:
                    # Too bad, let's put it back:
                    mc.xform(newInf, matrix=currentMtx, worldSpace=True)

        return {"newInfluences":newInfs,
                "missingParents":missingParents,
                "dupeParentNames":dupeParentNames,
                "goodParenting":goodParenting}

class SkinChunk(Chunk):
    r"""
    A SkinChunk is a collection of weight-based data for a given mesh, for it's
    verts.  The verts it collects data for could be one, or all, based on what is
    provided.  This instance is serialized to disk via exportSkinChunks, and deserialized
    into memory via importSkinChunks, both calling to pickle.

    It stores out both the current worldspace positions for the deformed verts,
    the 'pre-deformed' worldspace locations of them (v1.1.0), to provide that option
    to the user during import.
    """

    @staticmethod
    def getByMeshName(meshShape:str, skinChunks:list):
        r"""
        Based on the leaf mesh shape name, and a list of SkinChunk instances, see
        if we can find a name match:  If we find a match by name, return that SkinChunk
        instance. Otherwise return None.

        Parameters:
        meshShape : string : The full path to the mesh shape.
        skinChunks : list : SkinChunk instances.

        Return : None / SkinChunk.
        """
        shapeLeaf = meshShape.split("|")[-1].split(":")[-1]
        match = None
        for skinChunk in skinChunks:
            if shapeLeaf ==  skinChunk.getMeshShapeName():
                match = skinChunk
                break
        return match

    @staticmethod
    def getByVertCountOrder(meshShape:str, skinChunks:list) -> list:
        r"""
        Based on the mesh shape, and a list of SkinChunk instances, see if we can
        find a SkinChunks that has the same vert count and order.  It's up to the
        calling code to figure out if zero, or more than one is ok.

        Parameters:
        meshShape : string : The full path to the mesh shape.
        skinChunks : list : SkinChunk instances.

        Return : list : Of the matching SkinChunk instances.
        """
        checkVertCount = mc.polyEvaluate(meshShape, vertex=True)
        matches = []

        for skinChunk in skinChunks:
            if checkVertCount != skinChunk.getMeshVertCount():
                continue

            numSkinChunkNeighborSamples = skinChunk.getNumNeighborSamples()
            if not numSkinChunkNeighborSamples:
                # Odd a skinChunk would be saved without any, but this could provide
                # invalid data if we only rely on vertCount matching, so skip:
                continue

            skinChunkNeighbors = skinChunk.getVertNeighborSamples()
            checkNeighbors = utils.getVertNeighborSamples(meshShape, numSkinChunkNeighborSamples)
            neighborsMatch = True
            for key in skinChunkNeighbors:
                storedNeighbors = skinChunkNeighbors[key]
                currentNeighbors = checkNeighbors[key]
                if storedNeighbors != currentNeighbors:
                    neighborsMatch = False
                    break
            if neighborsMatch:
                matches.append(skinChunk)

        return matches

    #------------------

    def __init__(self, meshShape:str, vertIds:list, neighborSamples=10):
        r"""
        Create a new SkinChunk!

        Removed the args in v1.1.0 to make the call signature easier: This is all
        calculated in this method now rather than the calling code.
        * 'normals', 'weights', 'blendWeights', 'influences', 'skinninMethod'.

        Parameters:
        meshShape : string : The name of the skinned mesh shape node.  Internally
            will be converted to leaf name without namespace.  If not skinned, an
            AssertionError will be raised.
        vertIds : list : The int vert ids to store the data on.  This could be a
            different number (fewer) than the total the mesh has.
        neighborSamples : int : Default 10 : Will sample this many neighbor verts
            for *their* neighbors, to track vert order during reimport.
        """
        super(SkinChunk, self).__init__()

        mFnSkinCluster = utils.getMFnSkinCluster(meshShape) # MFnSkinCluster/None
        assert mFnSkinCluster, f"The provided mesh '{meshShape}' isn't skinned, can't save out SkinChunk data for it."
        skinClusterName = mFnSkinCluster.absoluteName()
        # Added 1.1.0, updated 1.1.1
        self.atBindPose = utils.getAtBindPose(skinClusterName)

        verts = ['%s.vtx[%s]'%(meshShape, index) for index in vertIds]
        influences = [inf.fullPathName() for inf in utils.getInfluenceDagPaths(meshShape)]

        # Store the leaf name, with no namespace
        self.meshShape = meshShape.split("|")[-1].split(":")[-1]
        self.meshVertCount = mc.polyEvaluate(meshShape, vertex=True)
        self.vertIds = vertIds
        self.weights = utils.getWeights(verts) # ndarray
        self.blendWeights = utils.getBlendWeights(verts)

        # Store the leaf name, with no namespace
        self.influences = [inf.split("|")[-1].split(":")[-1] for inf in influences]
        self.influenceMatrices = []
        localAttrs = ("translate", "rotate", "scale", "rotateAxis", "jointOrient")
        self.influenceLocalTransforms = []
        self.influenceRotateOrders = []
        self.influenceParents = []
        for inf in influences:
            infLeaf = inf.split("|")[-1].split(":")[-1]
            if self.influences.count(infLeaf) > 1:
                raise Exception("Duplicate influence node names provided based on this leaf name: %s"%infLeaf)

            # Grab the current world matrix:
            mtx = mc.xform(inf, query=True, matrix=True, worldSpace=True)
            if not self.atBindPose:
                # But it looks like we're not at the bindpose.  Can we query that
                # data from the joint node, presuming it is conected to a dagPose node?
                dagPose = mc.listConnections(f'{inf}.bindPose', source=False, destination=True, type='dagPose')
                if dagPose:
                    # This is the worldspace matrix it was in when skinned.  If
                    # there is no connection, getAttr will return None.
                    mtx = mc.getAttr(f'{inf}.bindPose')

            self.influenceMatrices.append(mtx)
            attrData = {}
            # New in 1.1.1 : Should be noted this data is meaningless erally if
            # we're not at the bind pose.
            for attr in localAttrs:
                # For some reasons Maya always returns these as [(x,y,z)]
                val = mc.getAttr(f"{inf}.{attr}")[0]
                attrData[attr] = val
            self.influenceLocalTransforms.append(attrData)
            self.influenceRotateOrders.append(mc.getAttr(f"{inf}.rotateOrder"))

            parent = mc.listRelatives(inf, parent=True, fullPath=True)
            if parent:
                self.influenceParents.append(parent[0].split("|")[-1].split(":")[-1])
            else:
                self.influenceParents.append(None) # World

        self.skinningMethod = mc.getAttr('%s.skinningMethod'%skinClusterName)
        self.totalMeshVerts = mc.polyEvaluate(meshShape, vertex=True)

        self.neighborSamples = neighborSamples

        verts = ['%s.vtx[%s]'%(meshShape, vid) for vid in vertIds]
        self.normals = utils.getVertNormals(verts)

        #self.vertPositions = [mc.pointPosition('%s.vtx[%s]'%(meshShape, vid)) for vid in vertIds]
        self.vertPositions = [mc.pointPosition(vert, world=True) for vert in verts]

        # The positions of the verts in the current worldspace location:
        meshShapeForPositions = utils.getPreDeformedShape(meshShape)


        # used for printing, to help the user know if this has this type of data
        # Saved out for it, since it could be duplicate.
        self.storePreDeformedData = False
        if not self.atBindPose and meshShapeForPositions != meshShape:
            # # Added 1.1.0
            # no reason to spend compute on this if we're at the bindPose, or if
            # somehoiw (not sure how) there is no predeformed shape node to query
            # These are the positions of the points at the bindpose, in worldspace:
            vertsPreDeformed = ['%s.vtx[%s]'%(meshShapeForPositions, vid) for vid in vertIds]
            self.vertPositionsPreDeformed = [mc.pointPosition(vert, world=True) for vert in vertsPreDeformed]
            self.normalsPreDeformed = utils.getVertNormals(vertsPreDeformed)
            self.storePreDeformedData = True
        else:
            # Just point to the same memory:
            self.vertPositionsPreDeformed = self.vertPositions
            self.normalsPreDeformed = self.normals

        self.creationTime = datetime.now()
        # This is set by exportSkinChunks.
        self.filePath = ""
        self.user = "Unknown"
        self.version = __version__
        try:
            self.user = os.getenv("USER")
        except:
            pass

        # Find neighbors:
        self.vertNeighbors = {}
        if neighborSamples:
            self.vertNeighbors = utils.getVertNeighborSamples(meshShape, neighborSamples)

    def __repr__(self):
        return "<%s object : %s >"%(self.__class__.__name__, self.meshShape)

    def __str__(self):
        return "%s : %s : %s verts"%(self.__class__.__name__, self.meshShape, len(self.vertIds))

    def printData(self, meshShape=True, skinMethod=True, meshVertCount=True,
                  numVerts=True, vertIds=True,
                  infNum=True, influences=True, hasPreDeformedData=True, atBindPose=True,
                  blendWeightsPerVert=True, infWeightsPerVert=True, normalsPerVert=True,
                  infListSlice=[0,-1], neighbors=True, creationDate=True, importPath=True,
                  user=True, version=True, rnd=4):
        r"""
        Print the information in this SkinChunk.  Seems to be missing calls to
        self.vertPositions & self.vertPositionsPreDeformed, self.normals & self.normalsPreDeformed :
        Should add those in at some point.

        Parameters:  NOTE : Adding new args here should also be reflected inside
            the App.populate method that builds these checkboxes for the user.

        meshShape : bool : Deafult True : If True, print the mesh shape name.
        skinMethod : bool : Default True : If True, print the skinning method.
        meshVertCount : bool : Default True : The total vert count of the mesh shape.
        numVerts : bool : Default True : If True, print how many vert weights are
            saved in this SkinChunk for the given mesh shape.  This could be a
            different number from meshVertCount, if the user saved a subset.
        vertIds : bool : Default True : If True, print the list of vert IDS saved
            by this SkinChunk for the meshShape.
        infNum : bool : Default True : If True, print the number of influences.
        influences : bool : Default True : If True, print the list of joint influences.
        hasPreDeformedData : bool : Default True : If True, print whether or not
            this SkinChunk stored out the 'pre-deformed' position and normal data
            at time of generation.
        atBindPose : bool : Added 1.1.1 : Was this saved with the mesh/influences
            in the bindpose?
        blendWeigtsPerVert : bool : Default True : If True, print the 'blend weights'
            for each vert.  These control the 'weight blended' values of that type
            of Skinning Method.  How much is displayed  is modified by infListSlice.
        infWeightsPerVert : bool : Default True : If True, print a list of vert ID's and
            their weights that correspond to the influences list.  How much is displayed
            is modified by infListSlice.
        normalsPerVert : bool : Default True : It True, print the stored worldspace
            normal for each vert.  How much is displayed  is modified by infListSlice.
        infListSlice : list : Default [0,-1] : Since the infWeightsPerVert
            can be quite large, adjusting these values are like slicing that list
            of values:  [10:20] would show you values 10-19 [0:50] would show the
            first 50 values, etc.  Default is to show them all.
        neighbors : bool : Default True : If True, print the target neighbor vert
            IDs based on the source verts originally sampled.
        creationDate : bool : Deafult True : Print when this SkinChunk was created.
        importPath : bool : Default True : Print the file this SkinChunk was imported
            from.
        user : bool : Default True : Return the name of the user who generated this
            SkinChunk.
        version : Print the version of the Skinner tool this was saved with.
        rnd : int : Default 4 : If printing the 'infWeightsPerVert', this will round
            the weight values.  If you want no rounding, enter 0 / None.
        """
        print("#-- SkinChunk ---------------------------------------------------")
        vertCount = len(self.vertIds)

        if infListSlice[0] > vertCount:
            newVal = vertCount - infListSlice[0]
            if newVal < 0:
                newVal = 0
            infListSlice[0] = newVal
        rndStr = ""
        if rnd:
            rndStr = "(rounded to %s decimals) "%rnd

        if infListSlice[1] > 1:
            if infListSlice[1] > vertCount:
                infListSlice[1] = vertCount
        elif infListSlice[1] == 0:
            infListSlice[1] = vertCount

        if meshShape:
            print("Mesh Shape : '%s'"%self.meshShape)
        if version:
            try:
                print("Generated with Skinner version : %s"%self.version)
            except AttributeError:
                # Possible someone with an old SkinChunk (pre Dec 7th, 2021) is
                # calling to this code.
                print("Generated with Skinner version : Unknown (old SkinChunk data)")
        if creationDate:
            print("Creation Date: %s"%self.getCreationTime())
        if importPath:
            print("Imported From: %s"%self.getFilePath())
        if user:
            print("Generated by user: '%s'"%self.getUser())
        if hasPreDeformedData:
            print("Has stored 'pre-deformed' position and normal data: %s"%self.getHasPreDeformedData())
        if atBindPose:
            print("Was saved at the bindpose: %s"%self.getAtBindPose())
        if skinMethod:
            print("Skinning Method : '%s'"%SKIN_METHODS[self.skinningMethod])
        if meshVertCount:
            print("Mesh Shape Vert Count: %s"%self.meshVertCount)
        if numVerts:
            print("Number Of Saved Vert (Weights) : %s"%(vertCount))
        if vertIds:
            print("Vert (Weight) IDs : %s"%(self.vertIds))
        if infNum:
            print("Number Of Influences : %s"%(len(self.influences)))
        if influences:
            print("Influences : %s"%(sorted(self.influences)))
        if blendWeightsPerVert:
            print("Blend Weights %s:"%rndStr)
            if infListSlice[0] != 0:
                print("\t...%s previous values..."%infListSlice[0])
            for vid in self.vertIds[infListSlice[0]:infListSlice[1]]:
                weight = self.getVertBlendWeight(vid)
                if rnd:
                    weight = round(weight, rnd)
                print("\tVert Index %s : %s"%(vid, weight))
            if infListSlice[1] != -1:
                if infListSlice[1] != numVerts:
                    if infListSlice[1] < 0:
                        print("\t...+%s more values..."%(abs(infListSlice[1])))
                    else:
                        print("\t...+%s more values..."%(  abs(numVerts-infListSlice[1]))  )

        if infWeightsPerVert:
            print("Influence Weights %s:"%rndStr)
            if infListSlice[0] != 0:
                print("\t...%s previous values..."%infListSlice[0])
            for vid in self.vertIds[infListSlice[0]:infListSlice[1]]:
                weights = self.getVertWeight(vid)
                if rnd:
                    weights = [round(weight, rnd) for weight in weights]
                print("\tVert Index %s : %s"%(vid, weights))
            if infListSlice[1] != -1:
                if infListSlice[1] != numVerts:
                    if infListSlice[1] < 0:
                        print("\t...+%s more values..."%(abs(infListSlice[1])))
                    else:
                        print("\t...+%s more values..."%(  abs(numVerts-infListSlice[1]))  )

        if normalsPerVert:
            print("Vert Normals %s:"%rndStr)
            if infListSlice[0] != 0:
                print("\t...%s previous values..."%infListSlice[0])
            for vid in self.vertIds[infListSlice[0]:infListSlice[1]]:
                normal = self.getVertNormal(vid)
                if rnd:
                    normal = normal.round(rnd)
                print("\tVert Normal %s : %s"%(vid, normal))
            if infListSlice[1] != -1:
                if infListSlice[1] != numVerts:
                    if infListSlice[1] < 0:
                        print("\t...+%s more values..."%(abs(infListSlice[1])))
                    else:
                        print("\t...+%s more values..."%(  abs(numVerts-infListSlice[1]))  )

        if neighbors:
            print ("Neighbor Indices for %s verts:"%(len(self.vertNeighbors)))
            for vid in sorted(self.vertNeighbors):
                neighbors = self.vertNeighbors[vid]
                print("\tVert Index %s : %s"%(vid, neighbors))


    #----------
    # Getters

    def getMeshShapeName(self) -> str:
        r"""
        Return the leaf mesh shape node string name.
        """
        return self.meshShape

    def getNumNeighborSamples(self) -> int:
        r"""
        Return the int number of neighbor sample points used at time of storage.
        """
        return self.neighborSamples

    def getVertNeighborSamples(self) -> dict:
        r"""
        Return the dict of self.vertNeighbors stored during init.
        """
        return self.vertNeighbors

    def getVertWeight(self, vertId) -> list:
        r"""
        Get the influence weights for the provided vert ID, as a list.
        """
        if vertId not in self.vertIds:
            raise Exception("Vert ID '%s' isn't part of this SkinChunk"%vertId)
        index = self.vertIds.index(vertId)
        return self.weights[index]

    def getVertBlendWeight(self, vertId:int) -> float:
        r"""
        Get the float 'blend weight' (used by 'Weight Blended' skinClusters) for the
        provided vert ID, as a float.

        Parameters:
        vertId : int

        Return : float
        """
        if vertId not in self.vertIds:
            raise Exception("Vert ID '%s' isn't part of this SkinChunk"%vertId)
        index = self.vertIds.index(vertId)
        return self.blendWeights[index]

    def getVertNormal(self, vertId:int, preDeformed=False) -> list:
        r"""
        Get the vert normal for the given vert ID, as a list.

        Parameters:
        vertId : int
        preDeformed : bool : Default False : New as of v1.1.0 : If True, query
            the 'pre-deformed' vertext normal.  Otherwise query the vert normal
            in the worldspace position the mesh was in during export.

        Return : list : The xyz normal.
        """
        if vertId not in self.vertIds:
            raise Exception("Vert ID '%s' isn't part of this SkinChunk"%vertId)
        index = self.vertIds.index(vertId)
        if not preDeformed:
            return self.normals[index]
        else:
            return self.normalsPreDeformed[index]

    def getVertIds(self) -> list:
        r"""
        Return a list of int vert IDs the weights were stored on.
        """
        return self.vertIds

    def getNumVerts(self) -> int:
        r"""
        Return an int for the number of verts stored.  This could be different
        from getMeshVertCount, if only a subset was stored.
        """
        return len(self.vertIds)

    def getMeshVertCount(self) -> int:
        r"""
        Return the original number of verts on the mesh when the weights were
        saved out.  This could be different from the actual number of vert weights
        saved, in self.vertIds/getNumVerts, if the user passed in a subset.
        """
        return self.meshVertCount

    def getSkinningMethod(self) -> int:
        r"""
        Return the int skinning method used by this SkinChunk, as spec'd by the
        SKIN_METHODS global.
        Same list indexed values values as the skinCluster.skinningMethod enum:
        "classic linear", "dual quaternion", "weight blended"
        """
        return self.skinningMethod

    def getCreationTime(self) -> datetime:
        r"""
        Return the datetime.datetime class instance that saved when this SkinChunk
        was craeted.
        """
        return self.creationTime

    def getFilePath(self) -> str:
        r"""
        Return the file path this SkinChunk was imported from, presuming it was.

        Return : string : If imported from a sknr file, this will be the that to
            that file.  If generated live, this will be an empty string.
        """
        return self.filePath

    def getUser(self) -> str:
        r"""
        Return the string username for who generated this SkinChunk.  If it couldn't
        be calculated via 'getenv USER', 'Unknown' is returned.
        """
        return self.user

    def getVersion(self) -> str:
        """
        Return the string version of the Skiner tool this SkinChunk was created with.
        """
        return self.version

    def getHasPreDeformedData(self) -> bool:
        """
        Introduced in 1.1.0.
        Returns True if this SkinChunk had 'preDeformed' data stored out for it
        when created.
        """
        if hasattr(self, "storePreDeformedData"):
            return self.storePreDeformedData
        else:
            return False

    def getAtBindPose(self) -> bool:
        """
        Introduced 1.1.1
        Returns bool if when this SkinChunk was created, the mesh and its influences
        were in the bindpose.
        """
        try:
            return self.atBindPose
        except AttributeError:
            # because how would we know?
            return False

    #----------
    # Setters

    def setFilePath(self, filePath:str):
        r"""
        Set the file path this SkinChunk was imported from.  This is called to by
        exportSkinChunks.

        Parameters:
        filePath : string : The full path to the .sknr file that imported this
            SkinChunk.
        """
        self.filePath = filePath

class UberChunk(Chunk):
    r"""
    A UberChunk is a collection of multiple SkinChunks:  Effectively a point-cloud
    of data that can be polled when individual mesh names can't be name matched
    with SkinChunks.
    """
    def __init__(self, skinChunks:list):
        r"""
        Initialzie our UberChunk.

        Parameters:
        skinChunks : list : The SkinChunk instances to store/combine.
        """
        super(UberChunk, self).__init__()
        if not isinstance(skinChunks, (list, tuple)):
            skinChunks = [skinChunks]

        self.skinChunks = skinChunks

        # Things that UberChunks don't have vs SkinChunks.  Just as a reminder:
        self.meshShape = None
        self.vertIds = None
        self.vertNeighbors = None

        #-------------------------
        # Initialized in the superclass, but commented here again for my brain.
        #self.influences = []
        #self.influenceMatrices = []
        #self.influenceLocalTransforms = [] # Added 1.1.1
        #self.influenceRotateOrders = [] # Added 1.1.1
        #self.influenceParents = []
        #self.weights = []
        #self.blendWeights = []
        #self.normals = []
        #self.normalsPreDeformed = [] # Added 1.1.0
        #self.vertPositions = []
        #self.vertPositionsPreDeformed = [] # Added 1.1.0

        for skinChunk in self.skinChunks: # type: SkinChunk
            # Figure out all influences
            chunkInfs = skinChunk.getInfluences()
            infParents = skinChunk.getInfluenceParents()
            infMatrices = skinChunk.getInfluenceMatrices()
            infLocalTransforms = skinChunk.getInfluenceLocalTransforms()
            infRotateOrders = skinChunk.getInfluenceRotateOrders()
            for i,inf in enumerate(chunkInfs):
                if inf not in self.influences:
                    self.influences.append(inf)
                    self.influenceMatrices.append(infMatrices[i])
                    self.influenceLocalTransforms.append(infLocalTransforms[i])
                    self.influenceRotateOrders.append(infRotateOrders[i])
                    self.influenceParents.append(infParents[i])
            self.vertPositions.extend(skinChunk.getVertPositions())
            self.vertPositionsPreDeformed.extend(skinChunk.getVertPositions(preDeformed=True))
            self.normals.extend(skinChunk.getAllNormals())
            self.normalsPreDeformed.extend(skinChunk.getAllNormals(preDeformed=True))

        # A placeholder list we can copy below
        zeroWeights = [0 for i in range(len(self.influences))]
        # Populate self.weights and self.blendWeights, based on all the passed
        # in SkinChunk instances.
        for skinChunk in self.skinChunks:
            #-----------
            # Weights

            # Each item is a sublist corresponding to the same index
            # in vertIds : The sublist are weights in relationship to the passed in
            # influences list.
            chunkWeights = skinChunk.getAllWeights()
            # list of string names for all influences.
            chunkInfs = skinChunk.getInfluences()
            # cWeights is a list of weights
            for cWeights in chunkWeights:
                # Make our list of empty weights to update:
                weights = zeroWeights[:]
                for i in range(len(cWeights)):
                    inf = chunkInfs[i]
                    weightIndex = self.influences.index(inf)
                    weights[weightIndex] = cWeights[i]
                self.weights.append(weights)

            #-----------
            # Blend Weights
            # A list of all the blendWeight values for all the verts in this UberChunk.
            chunkBlendWeights = skinChunk.getAllBlendWeights()
            self.blendWeights.extend(chunkBlendWeights)

        self.totalMeshVerts = len(self.weights)

    def __str__(self):
        return "%s : %s : %s verts"%(self.__class__.__name__, self.getMeshShapes(), self.getMeshVertCount())

    def __repr__(self):
        return "<%s object : %s >"%(self.__class__.__name__, self.getMeshShapes())

    #------------------
    # Getters

    def getSkinChunks(self) -> list:
        r"""
        Return a list of all the SkinChunk instances assigned to this UberChunk.
        """
        return self.skinChunks

    def getMeshShapes(self) -> list:
        r"""
        Return a leaf-name sorted list of all the mesh shape names used by this UberChunk.
        """
        return sorted([skinChunk.getMeshShapeName() for skinChunk in self.getSkinChunks()])

    def getMeshVertCount(self) -> int:
        r"""
        Return the total number of verts stored in this UberChunk.
        """
        return self.totalMeshVerts

#-----------------------------
# Generate & Export

@utils.waitCursor
def generateSkinChunks(meshShapeVertIds:dict, setToBindPose=False,
                       verbose=True, promptOnNonInteractiveNormalization=True) -> list:
    r"""
    Create the SkinChunk data to store to disk based on the provided items.

    Future updates:
    * store incoming connections to any influences/ transform values, set to
        bindbpose before generation, generate the SkinChunks, then reset the transforms
        and connections. OR: Read vert positions from the intermediateObjects.

    Parameters:
    meshShapeVertIds : dict : keys are mesh shape names, values are lists of int vert IDs.
        You can get this from utils.getMeshVertIds().
    setToBindPose : bool : Default False : Should the mesh be set to its bindpose
        before the SkinChunks are generated?  If exportPreDeformedPoints=True, then
        there's no reason for this to be True.  If True, and any influences can't
        be set to their bind pose, an Exception will be raised.  If there is no
        dagPose node present to query the bind pose transforms on, it will be skipped.
    promptOnNonInteractiveNormalization : bool : Default True : If True, and if
        skinCluter node are found with their normalizeWeights value set to anything
        other than 1 (interactive), it will prompt the user to see if it should
        auto-convert the clusters to interactive.  If this is set to False, or if
        they cancel, the skinChunk generation will fail.

    Return : list : Each item is a SkinChunk instance.  Can be exported to disk
        via exportSkinChunks.
    """
    timeStart = time.time()
    skinChunks = []

    missingSkinning = []
    meshShapes = []
    skinClusters = []
    nonInteractive = []
    for meshShape in meshShapeVertIds:
        meshShapes.append(meshShape)
        mFnSkinCluster = utils.getMFnSkinCluster(meshShape) # MFnSkinCluster/None
        if mFnSkinCluster:
            skinCluster = mFnSkinCluster.absoluteName()
            skinClusters.append(skinCluster)
            skinMethod = mc.getAttr('%s.skinningMethod'%skinCluster)
            if skinMethod < 0:
                # Have seen this happend from imported FBX data.
                skinMethod = 0
            if mc.getAttr('%s.normalizeWeights'%skinCluster) != 1: # 0 = none, 1 = interactive, 2 = post
                nonInteractive.append(skinCluster)
        else:
            missingSkinning.append(meshShape)

    assert not missingSkinning, "These mesh shapes are missing skinning: %s"%missingSkinning

    utils.validateInteractiveNormalization(skinClusters, promptOnNonInteractiveNormalization=promptOnNonInteractiveNormalization)

    if setToBindPose:
        poseFail = []
        for skinCluster in skinClusters:
            poseResult = utils.setBindPose(skinCluster)
            if poseResult is False:
                # None = "Has no dagPose to set to bindPose", so just skip those.
                poseFail.append(skinCluster)
        if poseFail:
            print("skinClusters that can't be set to their 'bind pose':")
            for skinCluster in poseFail:
                print("    %s"%skinCluster)
            raise Exception("Failed to set all skinClusters to their bind pose, see errors above ^")

    if verbose:
        print("Generating SkinChunks...")
    hideProgress = not mc.about(batch=True)
    with utils.ProgressWindow(len(meshShapeVertIds), enable=hideProgress, title="Generating Skin Chunks") as progress:
        for i,meshShape in enumerate(meshShapes):
            if not progress.update(meshShape.split("|")[-1]):
                om2.MGlobal.displayWarning("SkinChunk generation canceled by user")
                return None
            indices = meshShapeVertIds[meshShape]
            skinChunk = SkinChunk(meshShape, indices)
            if verbose:
                print("\t%s : Based on %s total verts in the mesh."%(skinChunk, skinChunk.getMeshVertCount()))
            skinChunks.append(skinChunk)

    if verbose:
        timeEnd = time.time()
        timeTotal = timeEnd - timeStart
        om2.MGlobal.displayInfo("Generated SkinChunks in %.3f seconds."%(timeTotal))

    return skinChunks

@utils.waitCursor
def exportSkinChunks(filePath:str, skinChunks:list, verbose=True,
                     vcExportCmd=None, vcDepotRoot=None) -> bool:
    r"""
    Serialize the skinChunks to disk.  This also sets the filePath attribute on
    each of the SkinChunks based on the filePath arg.  The .sknr file is simply
    a pickled list of SkinChunk instances.

    VERY IMPORTANT : If you're using the vcExportCmd and using Perforce (possibly
    other VC types), you'll need to udpate your P4 filetypes list to set the .sknr
    format to be binary:
    Perforce sets undefined extensions/filetypes as ascii by default, and this will
    wreck .sknr data once it's put on the P4 server.  It will look/work correct
    on the PC of the *person that generated it*, but anyone else that syncs it:
    it will be broken, often with an error that looks something like:
    // Error: Exception: No module named 'skinner.core\r' //
    Note how a \r is embedded in the module name?  Not good.
    You can do this at a global level via `p4 typemap`, presuming  you have permissions:
    https://www.perforce.com/manuals/v19.2/cmdref/Content/CmdRef/p4_typemap.html

    Parameters:
    filePath : string : The full path on disk to the file to save.
    skinChunks : list : The return from generateSkinChunks, which is a list of
        SkinChunk instances.
    vcExportCmd : None / string : Default None. If provided, this is a string that will
        be executed (via exec), that should contain all the code needed by your
        version control software to edit/add the arg to 'filePath'.  The rule is,
        the filePath will be passed into this vcExportCmd string via string formatting,
        so it's required that somewhere in this string is a "'%s'" that we will
        string format.  Here is a simple example of the string (can be multiline
        if need be):
        vcExportCmd = "import p4; p4.open('%s')"
        And it is executed like so in the code below:
        exec(vcExportCmd%filePath)
        The behavior of this arg is modified by vcDepotRoot.
    vcDepotRoot : string / None : Default None : If this is provided, and it's a
        valid directory, then the tool will only attempt to manage the filePath
        with the vcExportCmd, if the filePath starts with the vcDepotRoot : This allows
        the tool to manage .sknr files in a project directory via version control,
        yet skip that code execution/management for things outside that path.
        If this is None, yet vcExportCmd is still provide, it will try to mange the
        file in version control regardless of where it lives, that may cause errors,
        which the tool will skip, but will print.

    Return : bool : True if successfull.
    """
    # Handle external version control:
    if vcDepotRoot:
        if os.path.isdir(vcDepotRoot):
            vcDepotRootCheck = vcDepotRoot.replace("\\", "/").lower()
            filePathCheck = filePath.replace("\\", "/").lower()
            if not filePathCheck.startswith(vcDepotRootCheck):
                vcExportCmd = None
        else:
            om2.MGlobal.displayWarning("skinner.core.exportSkinChunks : The arg provided to 'vcDepotRoot' is an invalid directory: Will be ignored (probably bad?): %s"%vcDepotRoot)

    if vcExportCmd:
        stringFormatted = False
        for sfmt in ("'%s'", '"%s"'):
            if sfmt in vcExportCmd:
                stringFormatted = True
                break
        if not stringFormatted:
            print(vcExportCmd)
            om2.MGlobal.displayError("skinner.core.exportSkinChunks : The string arg provided to vcExportCmd (see above) is invalid:  Must contain \"'%s'\" to do a string formatting replacement.  Skipping version control integration.")
        else:
            execStr = vcExportCmd%filePath.replace("\\","/")
            if verbose:
                print("Managing Skinner file via the version control call:")
                print("    ",execStr)
            try:
                exec(execStr)
            except Exception as e:
                if not verbose:
                    print("skinner.core.exportSkinChunks : Tried executing this passed in 'vcExportCmd' code:")
                    print("    ",execStr)
                print(str(e))
                om2.MGlobal.displayError("skinner.core.exportSkinChunks : Failed to manange in version control, see above ^")

    if os.path.isfile(filePath):
        if not os.access(filePath, os.W_OK):
            om2.MGlobal.displayError("skinner.core.exportSkinChunks : The provided file is read-only: '%s'"%filePath)
            return False

    if not isinstance(skinChunks, (list,tuple)):
        skinChunks = [skinChunks]
    timeStart = time.time()
    for skinChunk in skinChunks:
        skinChunk.setFilePath(filePath)
    try:
        dirName = os.path.dirname(filePath)
        if not os.path.isdir(dirName):
            os.makedirs(dirName)
        #if os.path.isfile(filePath):
            #if not os.access(filePath, os.W_OK):
                #raise IOError("The provided filepath is read-only: %s"%filePath)
        with open(filePath, 'wb') as outf:
            # The 'protocol' has been set to 2, which controls how return
            # characters are stored.  Use it.
            pickle.dump(skinChunks, outf, 2)
    finally:
        timeEnd = time.time()
    if verbose:
        timeTotal = timeEnd - timeStart
        om2.MGlobal.displayInfo("Exported SkinChunks in %.3f seconds: %s"%(timeTotal, os.path.normpath(filePath)))
    return True

#-----------------------------
# Import & Set

@utils.waitCursor
def importSkinChunks(filePaths:list, verbose=True) -> list:
    r"""
    Load the SkinChunk data stored on disk, and return that data.  The data is
    the return from generateSkinChunks.

    If multiple filePaths are provded, and they have overlapping SkinChunk data
    for the same named mesh shapes, only the most recently created ones are kept:
    'older ones' are popped out of the list.

    Parameters
    filePaths : string/list : The full paths to the .sknr files to import.  Multiple
        files are allowed.  These were previously saved by exportSkinChunks.
    verbose : bool : Default = True : Print the results?

    Return : list : The loaded SkinChunk instances.
    """
    if not np:
        raise ImportError("Unable to import the numpy module")
    if not KDTree:
        raise ImportError("Unable t0 import the scipy.spatial.KDTree module")

    if verbose:
        print("#----------------------------------------------------------")
        print("Skinner Importing SkinChunks....")
    if not isinstance(filePaths, (list,tuple)):
        filePaths = [filePaths]
    skinChunks = []
    timeStart = time.time()
    for fPath in filePaths:
        if not os.path.isfile(fPath):
            raise IOError("The provided file is missing from disk: %s"%fPath)
    try:
        for fPath in filePaths:
            with open(fPath, 'rb') as f:
                theseChunks = pickle.load(f)
                skinChunks.extend(theseChunks)
                if verbose:
                    print("\tImported %s SkinChunks from: %s"%(len(theseChunks), fPath))

            # If multiple SkinChunks were imported/merged that are based on the
            # same mesh shape, only keep the ones that are most current.

            # Note : If I want to get all fancy in the future I could try merging
            # this data if they had different vert IDs, and bias to the newer IDs,
            # but that will be complex if they have different influences.
            # Maybe, only merge if they have the same number of influences?  Or,
            # allow for multiple influences filling in zero vaules, but always bias
            # to the most recent weighting.
            chunkCreationTimes = []
            for skinChunk in skinChunks:
                thisMeshShape = skinChunk.getMeshShapeName()
                creationTime = skinChunk.getCreationTime()
                importFile = skinChunk.getFilePath()
                chunkCreationTimes.append([skinChunk, thisMeshShape, creationTime, importFile])

        # Remove anything old:
        for skinChunk in skinChunks[:]:
            thisCreationTime = skinChunk.getCreationTime()
            thisMeshShape = skinChunk.getMeshShapeName()
            thisImportFile = skinChunk.getFilePath()
            for checkChunk, checkShape, checkTime, checkImportFile in chunkCreationTimes:
                if thisMeshShape == checkShape:
                    if thisCreationTime > checkTime:
                        skinChunks.remove(checkChunk)
                        if verbose:
                            print("\tFound an older SkinChunk, removing:")
                            print("\t\tNewer (preserving): %s : %s : %s"%(skinChunk, thisCreationTime, thisImportFile))
                            print("\t\tOlder (removed)   : %s : %s : %s"%(checkChunk, checkTime, checkImportFile))

    finally:
        timeEnd = time.time()
    if verbose:
        timeTotal = timeEnd - timeStart
        om2.MGlobal.displayInfo("Imported %s SkinChunk(s) in %.3f seconds from: %s"%(len(skinChunks), timeTotal, filePaths))

    return skinChunks

@utils.waitCursor
def setWeights(items:list, skinChunks=None, filePath=None, createMissingInfluences=True,
               fallbackSkinningMethod="closestNeighbors",
               closestNeighborCount=6, closestNeighborDistMult=2.0,
               filterByVertNormal=False, vertNormalTolerance=0.0,
               closestPointFunc=closestPointKdTree, unskinFirst=False,
               setToBindPose=False, importUsingPreDeformedPoints=True,
               forceUberChunk=False, matchByVertCountOrder=True,
               postSmooth=2, postSmoothWeightDiff=0.25,
               selectVertsOnly=False, verbose=True, promptOnNonInteractiveNormalization=True) -> dict:
    r"""
    Set the weights / blendWeights (if the skinCluster in question is set to 'weight
    blended') on the provided items, based on either a list of SkinChunk
    instances, or a file path previously saved by exportSkinChunks.

    Parameteres:
    items : list : The string names of verts ('meshName.vtx[#]',...) or mesh shape
        / transform name.  Can mix and match.  Note, weights are stored by mesh
        shape name, not transform name: Shape name is more important.
    skinChunks : list/None : Default None : If not None, a list of SkinChunk
        instances. If this is None, filePath must be valid.
    filePath : string/None : If not None, the full path of the weight file to import,
        presumably previously saved via exportSkinChunks.
        If this is None, skinChunks must be valid.
    createMissingInfluences : bool : Default True : Create any missing influences
        (joints) that this skinning requires?  If False, and any are missing, the
        import will fail.  If the mesh is already skinned, and setToBindPose is
        False, setToBindPose will be set to True automatically before any missing
        influences are created / parented into the hierarchy.
    fallbackSkinningMethod : string : Default "closestNeighbors" : If there isn't a
        1:1 vert:weight match, how do we figure out the weight?  "closestPoint"
        will find the closest target vert, and use that influence/weight info.
        "closestNeighbors" will use the logic (slower, but probably better results).
    closestNeighborCount : int : Default 6 :  If fallbackSkinningMethod is
        "closestNeighbors" : How many verts should be sampled to generate the
        new weight influences.  This is the max value, only verts found within
        'closest first distance * closestNeighborDistMult' will be considered.
        0 or -1 mean use 'all the neighbors' for the calculation, which will be
        slower.
    closestNeighborDistMult : float : Default 2.0 : If fallbackSkinningMethod is
         "closestNeighbors" : This defines the 'search bubble distance'
        when looking for other close verts:  If the closest vert is 1 unit away,
        the tools will search with a radius of 1 unit * closestNeighborDistMult
        for other positions\influences.
    closestPointFunc : function/None : Default closestPointKdTree : If None, use
        closestPointBruteForce : The 'closest point function' to use.  Broken out
        as an arg so you can pass in your own, if you got something faster than
        what this tool uses.  See the docstring of closestPointExample if you want
        to roll your own.
    unskinFirst : bool : Default False : If True, and a mesh having weights imported
        on it is already skinned:  Unskin it first.  Note:  It appears that the
        plugin command to set weights will occasionally crash if this is set to
        False, and the skinCluster that its setting weights on wasn't previously
        made with this tool.  Clearly a bug, needs to be addressed, so keeping
        this arg set to True by default is safer, but more limiting when reading
        in subsections of vert weights on something already skinned.
        If this is set to True, then importUsingPreDeformedPoints is automatically
        set to False, since there would be no 'pre-deformed' points to query, as
        the mesh will have skinning removed assuming the shape of the bindpose.
    setToBindPose : bool : Default False : If the mesh is arleady skinned, should
        it be set to the bindpose before weights are set?  This is unecessary if
        importUsingPreDeformedPoints=True.  However, if createMissingInfluences
        is True and missing influences are found, then it must be set to the bindpose
        so they can be created/parented into the hierarchy correclty.
    importUsingPreDeformedPoints : bool : Default True : Introduced in 1.1.0 : When
        importing, if using a 'fallback skinning method' to interpolate values,
        if this is checked, the worldspace positions of the 'pre-deformed' mesh
        shape (aka, the intermediateObject) will be used instead of whatever current
        worldspace pose it's in: By setting this, you can import skinning without
        having to 'zero' your skeleton first.  Also, setting this to True will get
        weights from the SkinChunk's 'pre-deformed position pool' basd on when it
        was saved, since generally if you want to import based pre-deformed positions,
        You'd want to query the same pre-deformed points in the SKinCluster.
        If this is True, setToBindPose is unecessary, and should be False.  If
        unskinFirst is True, this is auto-set to False:  See the reasoning above.
    forceUberChunk : bool : Default False : If True, bypass all the descending
        logic of trying to match weighst by mesh name, and load them instead entirely
        from the UberChunk... aka, worldspace point cloud based on the algorithm
        defined in fallbackSkinningMethod.  Why would you want to do this?  Mostly
        troubleshooting, generally you wouldn't.
    matchByVertCountOrder : bool : Defaylt True : When loading the weights, if there is
        no name match, if this is True:  Look through the skinChunks for a vert
        count / vert order match:  If a single one is found, then use that, and
        load in by vert ID.  This makes it handy to copy weights between mesh that
        are 'the same', but with different names.  Note, if forceUberChunk is True,
        this is auto-set to False.
    postSmooth : int : Default 2 : Should the skinning be smoothed after import?
        If so, this is the number of iterations it should be smoothed.
        This is ran on all the outcomes except when loaded on by 1:1 vert count/
        order: In that case, it's disabled, since there's no point and could change
        the look.  NOTE:  If loading in by 1:1 vert ID, no skinning will be applied.
    postSmoothWeightDiff : float : Default .25 : If postSmooth is some positive
        value, this is the logic Maya applies to see if a given vert should have
        its weights smoothed : If abs(vertAweight - vertBweight) > postSmoothWeightDiff
        value, then smooth it.  So the LOWER you set this value, the MORE verts
        will get smoothed, and the HIGHER you set this value the FEWER verts will
        be smoothed.  For example, if vA has a weight of .5, and vB has a weight
        of .6 : abs(.5 - .6) = 0.1:  It will only be smoohted if postSmoothWeightDiff
        is less than .1
    selectVertsOnly : bool : Default False : If True, don't perform any skinning,
        but instead select the verts that would get skinning applied.  Note, having
        this checked will cause the weight set to fail under a number ofconditions,
        any of which would require a change to the skinCluster (say, adding new
        influences, missing joints) before the weights were set.
    verbose : bool : Default True : Print the results?
    promptOnNonInteractiveNormalization : bool : Default True : If True, and if
        skinCluter node are found with their normalizeWeights value set to anything
        other than 1 (interactive), it will prompt the user to see if it should
        auto-convert the clusters to interactive.  If this is set to False, or if
        they cancel, the weight setting will fail.

    Return : dict : Keys are the mesh that were imported on. values are sub-dicts
        with k:v paris for :
            "totalTime":seconds,
            "importMethod":"the method used",
            "success":bool, where it's True if the weights were set, and False if
                something went wrong.
            "newInfluences" : list : The full path to any new joints created, presuming
                some were missing and createMissingInfluences=True. v1.0.15
        This data can be used to generate 'import reports' for users.
    """


    closestNeighborCountStr = str(closestNeighborCount)
    if closestNeighborCount == -1:
        closestNeighborCountStr = "All"

    if not np:
        raise ImportError("Unable to import the numpy module")
    if not KDTree:
        raise ImportError("Unable to import the scipy.spatial.KDTree module")

    assert fallbackSkinningMethod in ("closestPoint", "closestNeighbors"), "fallbackSkinningMethod '%s' is invalid"%fallbackSkinningMethod
    if verbose:
        print("#----------------------------------------------------------")
        print("Skinner Weight Setting....")
    if not skinChunks and not filePath:
        raise Exception("Need to provide either skinChunks or filePath")

    selectMe = []
    ret = {}

    # Validate our input data...
    if not skinChunks:
        if not filePath:
            raise Exception("Need to provide either a list of SkinChunk data to'skinChunks', or a valid file to 'filePath':  Got neither.")
        if not os.path.isfile(filePath):
            raise IOError("%s is missing from disk"%filePath)
        skinChunks = importSkinChunks(filePath)
        if not all([isinstance(data, SkinChunk) for data in skinChunks]):
            print(skinChunks)
            raise Exception("The data (see above) inside the provided file isn't all SkinChunk instances:  Invalid file: %s"%filePath)
    if not isinstance(skinChunks, (list,tuple)):
        skinChunks = [skinChunks]
    if not all([isinstance(data, SkinChunk) for data in skinChunks]):
        print(skinChunks)
        raise Exception("The data provided by the skinChunks argument isn't all SkinChunk instances:  Invalid data, see above.")
    # Validation complete

    timeStart = time.time()
    mc.undoInfo(openChunk=True, chunkName="setWeights")
    try:
        #-------------------------------------------------------------
        # Based on what was proivded to import on, break it down to individual verts:
        # meshShapeVertIds dictionary's keys are mesh shape names, and the values
        # are lists of the previously saved int vert IDs to import onto.
        meshShapeVertIds = utils.getMeshVertIds(items=items)

        # Make sure if there is existig skinning, the skinCluster nodes have their
        # normalization set to interactive.  If the tool doesn't auto fix it, an
        # Exception will be raised.
        skinClusters = []
        for meshShape in meshShapeVertIds:
            mFnSkinCluster = utils.getMFnSkinCluster(meshShape) # MFnSkinCluster/None
            if mFnSkinCluster:
                skinClusters.append(mFnSkinCluster.absoluteName())
        utils.validateInteractiveNormalization(skinClusters, promptOnNonInteractiveNormalization=promptOnNonInteractiveNormalization)

        #-----------------------------------------------------------------------
        # Start caluclating per-mesh import data

        # Only calculate if we have to:
        uberChunk = None
        if forceUberChunk:
            matchByVertCountOrder = False
            uberChunk = UberChunk(skinChunks)
            if verbose:
                print("\tBecause 'forceUberChunk=True', generated:", uberChunk)

        hideProgress = not mc.about(batch=True)
        with utils.ProgressWindow(len(meshShapeVertIds), enable=hideProgress) as progress:
            for meshShape in meshShapeVertIds:
                meshLeafName = meshShape.split("|")[-1]
                # Values will be updated below.
                thisRetData = {"totalTime":0.0,
                               "importMethod":"None",
                               "success":True}
                doPostSmooth = postSmooth
                # MFnSkinCluster node assigned to the mesh, or None.
                mFnSkinCluster = utils.getMFnSkinCluster(meshShape)

                if not progress.update(meshShape.split("|")[-1]):
                    om2.MGlobal.displayWarning("Skin import canceled by user")
                    return

                if verbose:
                    print("#----------------------------------------------------------")

                meshVertCount = mc.polyEvaluate(meshShape, vertex=True)
                #-------------------
                # This is what we're importing onto:
                importVertIds = meshShapeVertIds[meshShape]
                importVertNames = ["%s.vtx[%s]"%(meshShape, vid) for vid in importVertIds]
                numImportOntoVerts = len(importVertIds) # The number of verts we're importing onto

                if verbose:
                    print("Importing on %s verts of mesh: %s"%(numImportOntoVerts, meshShape))


                #-------------------------------------------------------------------
                #-------------------------------------------------------------------
                # SKINCHUNK AND UBERCHUNK SETUP

                skinChunk = None # type: SkinChunk
                importFromUberChunk = False
                foundSkinChunkNameMatch = False

                if forceUberChunk:
                    importFromUberChunk = True
                else:
                    skinChunk = SkinChunk.getByMeshName(meshShape, skinChunks)
                    if not skinChunk:
                        if matchByVertCountOrder:
                            # See if we can find a matching skinChunk by vert count
                            # and order:
                            checkChunks = SkinChunk.getByVertCountOrder(meshShape, skinChunks)
                            if len(checkChunks) == 1:
                                skinChunk = checkChunks[0]
                                origMeshName = skinChunk.getMeshShapeName()
                                if verbose:
                                    print("\tFound no SkinChunk by name match for mesh '%s', but found one by matching vert count / order based on the saved values of '%s'!"%(meshLeafName, origMeshName))

                        if not skinChunk:
                            if verbose:
                                if matchByVertCountOrder:
                                    print("\tNo SkinChunk for mesh named '%s', and found no other SkinChunk vert count/order match: Will use UberChunk"%meshLeafName)
                                else:
                                    print("\tNo SkinChunk for mesh named '%s': Will use UberChunk"%meshLeafName)

                            importFromUberChunk = True
                            if not uberChunk:
                                uberChunk = UberChunk(skinChunks)
                                if verbose:
                                    print("\tUberChunk does not exist yet, created:", uberChunk)
                    else:
                        foundSkinChunkNameMatch = True
                        if verbose:
                            print("\tFound:", skinChunk)

                #-------------------------------------------------------------------
                #------------------------------------------------------------------
                # Get the saved influence names, and make sure none are missing, or
                # there are duplicates.

                skinChunkInfNames = [] # String names, leaf
                infNameData = OrderedDict() # Keys are leaf names, values are full path names.
                theChunk = None
                if skinChunk:
                    # list of strings leaf names
                    skinChunkInfNames = skinChunk.getInfluences()
                    theChunk = skinChunk
                elif uberChunk:
                    # list of strings leaf names
                    skinChunkInfNames = uberChunk.getInfluences()
                    theChunk = uberChunk
                missingInfs = []
                multipleInfs = []
                newInfs = []
                existingSkinClusters = []

                # Look for these joints in the scene: Hope you find just one!
                for sin in skinChunkInfNames:
                    occurances = mc.ls(sin, long=True, type='joint')
                    if not occurances:
                        missingInfs.append(sin)
                    elif len(occurances) > 1:
                        multipleInfs.append(occurances)
                    else:
                        infNameData[sin] = occurances[0]
                        # Is this joint connected to an existing skinCluster?  We
                        # need to know in case 'Set To Bindpose' is set:
                        outSkinClusters = mc.listConnections(f"{occurances[0]}", source=False, destination=True, type="skinCluster")
                        if outSkinClusters:
                            for osc in outSkinClusters:
                                if osc not in existingSkinClusters:
                                    existingSkinClusters.append(osc)
                if mFnSkinCluster and mFnSkinCluster.name() not in existingSkinClusters:
                    existingSkinClusters.append(mFnSkinCluster.name())

                assert not multipleInfs, "For mesh '%s', found multiple joint influences in the scene with the same names.  How does Skinner know which one should be used? : %s"%(meshShape, multipleInfs)

                if missingInfs and not createMissingInfluences:
                    raise Exception("For '%s', missing these influences, and 'createMissingInfluences=False': %s"%(meshShape, missingInfs))

                if missingInfs and existingSkinClusters:
                    if verbose and not setToBindPose:
                        print(f"\tThe scene is missing joint influences required for skinning (see below), and needed existing influences in the scene have skinning on them, but 'setToBindpose=False' : Auto-forcing 'setToBindpose=True' before we can make/parent the missing influences.")
                    setToBindPose = True

                #-------------------------------------------------------------------
                #-------------------------------------------------------------------
                # SET TO BINDPOSE

                if setToBindPose:
                    # Do this before we unskin it, below.

                    if verbose and existingSkinClusters:
                        print("\tSetting related (via SkinCluster influences, or existing skinning) skinCluster nodes to their bindpose:")

                    noPoseSc = []
                    for skinCluster in sorted(existingSkinClusters):
                        # If already skinned, set to the bindpose before we detach
                        # skinning, or add any influences, or just if the user had
                        # that option set.
                        poseResult = utils.setBindPose(skinCluster)
                        if poseResult is False:
                            noPoseSc.append(skinCluster)
                            if verbose:
                                print(f"\t\t{skinCluster} : Failed")
                        elif verbose:
                            print(f"\t\t{skinCluster} : Success")

                    if noPoseSc:
                        thisRetData['success'] = False
                        thisRetData['importMethod'] = "Unable to set bindpose: No import performed"
                        print("    %s :"%meshShape)
                        print("    Error : Unable to set these related skinClusters to their bindpose: %s"%skinCluster)
                        ret[meshShape] = thisRetData
                        continue

                #-------------------------------------------------------------------
                #-------------------------------------------------------------------
                # UNSKIN

                if unskinFirst:
                    if selectVertsOnly:
                        raise Exception("selectVertsOnly=True, but unskinFirst=True also:  Unskinning will cause a chnage in skinning, probably undesirably.")
                    # Since we're removing any existing skinning, there won't be
                    # 'pre-deformed' data to query, since the mesh will revert back
                    # to the bindpose.
                    if importUsingPreDeformedPoints:
                        importUsingPreDeformedPoints = False
                        if verbose:
                            print("\tWas previously skinned, and 'unskinFirst=True', but also 'importUsingPreDeformedPoints=True': This is incompatible, setting 'importUsingPreDeformedPoints=False'.")

                    if mFnSkinCluster :
                        unbindStart = time.time()
                        mc.skinCluster(meshShape, edit=True, unbind=True)
                        unbindEnd = time.time()
                        totalUnbmindTime = unbindEnd-unbindStart
                        mFnSkinCluster = None
                        if verbose:
                            print("\tWas previously skinned, and 'unskinFirst=True':  Removed skinning in %.3f seconds"%totalUnbmindTime)

                #-------------------------------------------------------------------
                #-------------------------------------------------------------------
                # CREATE MISSING INFLUENCES

                if missingInfs and createMissingInfluences:
                    if selectVertsOnly:
                        raise Exception("selectVertsOnly=True, but missing influences were found, and createMissingInfluences=True: This will cause a scene change, possibly undesirably.")
                    # would have errored above if we got in here and createMissingInfluences=False
                    newInfResults = theChunk.buildMissingInfluences()
                    newInfluences = newInfResults["newInfluences"] # Leaf names
                    missingParents = newInfResults["missingParents"]
                    dupeParentNames = newInfResults["dupeParentNames"]
                    goodParenting = newInfResults["goodParenting"]
                    for newInf in newInfluences:
                        fullPath = mc.ls(newInf, long=True, type='joint')[0]
                        if fullPath not in newInfs:
                            newInfs.append(fullPath)
                        infNameData[newInf] = fullPath

                    if verbose:
                        print("\tCreating & Parenting %s Missing Influences:"%(len(newInfluences)))
                        if not missingParents and not dupeParentNames:
                            print("\t\tSuccessfully created and re-parented all %s missing influences: They are shown as ['newInfluence', 'oldParent'] below:"%(len(newInfluences)))
                            print("\t\t\t", goodParenting)
                        else:
                            print("\t\tCreated these %s missing influences, but had some issues with parenting, see below: %s"%(len(newInfluences), newInfluences))
                            if missingParents:
                                print("\t\t\tFor each ['newInfluence', 'oldParent'] pair, the 'oldParent' is missing. 'newInfluence' has been parented to the world:")
                                print("\t\t\t\t", missingParents)
                            if dupeParentNames:
                                print("\t\t\tFor each ['newInfluence', ['list of duplicate names'] ] pair, the 'list of duplicate names' is confusing the parent operation: 'newInfluence' has been parented to the world:")
                                print("\t\t\t\t", dupeParentNames)

                #-------------------------------------------------------------------
                #-------------------------------------------------------------------
                # UPDATE SKINCLUSTER WITH INFLUENCES
                skinClusterInfluenceNames = []
                if not mFnSkinCluster:
                    if selectVertsOnly:
                        raise Exception("selectVertsOnly=True, but the current mesh is unskinned, incompatible settings.")
                    # If the mesh isn't currently skinned, skin it to the same influences
                    # that are in the weight data (SkinChunk or UberChunk).
                    if verbose:
                        print("\tMaking SkinCluster for '%s'..."%meshLeafName)
                    startDefaultSkin = time.time()

                    # Fascinating tidbit:  Maya will error when making skinClusters
                    # on hidden mesh shape nodes.
                    if not mc.getAttr(f"{meshShape}.visibility"):
                        mc.setAttr(f"{meshShape}.visibility", 1)
                    scName = mc.skinCluster(list(infNameData.values()), meshShape, dropoffRate=10.0,
                                            maximumInfluences=1, toSelectedBones=True,
                                            name='skinnerCluster#')[0]

                    mFnSkinCluster = utils.getMFnSkinCluster(meshShape) # MFnSkinCluster
                    skinClusterInfluenceNames = [dPath.fullPathName() for dPath in mFnSkinCluster.influenceObjects()]
                    endDefaultSkin = time.time()
                    defaultSkinTime = endDefaultSkin - startDefaultSkin
                    if skinChunk:
                        # If we found a skinChunk, then reapply the skinning method
                        # that was saved.
                        # 0 = linear, 1 = dualQuat, 3 = weightBlended.
                        skinMethod = skinChunk.getSkinningMethod()
                        if skinMethod < 0:
                            # bugfix bad FBX data.  This same work is done when
                            # Storing the SkinChunks, but 'just in case...'.
                            skinMethod = 0
                        mc.setAttr('%s.skinningMethod'%scName, skinMethod)
                        if verbose:
                            print("\t\tCreated: '%s', set skinning method to '%s' as saved in the SkinChunk, in %.2f seconds"%(scName, SKIN_METHODS[skinMethod], defaultSkinTime))
                    else:
                        if verbose:
                            print("\t\tCreated: '%s', set skinning method to 'linear' since previous SkinChunk data couldn't be found, in %.2f seconds"%(scName, defaultSkinTime))

                    if len(skinChunkInfNames) == 1:
                        # It only had one influence to begin with, and just got
                        # skinned to it:  No more work to do, done!
                        if uberChunk:
                            thisRetData["importMethod"] = "No Mesh Name Match (UberChunk) : Single Influence"
                        else:
                            thisRetData["importMethod"] = "Mesh Name Match (SkinChunk) : Single Influence"
                        thisRetData["totalTime"] = defaultSkinTime
                        if verbose:
                            print("\tOnly skinned to a single influence, skinning complete in %.2f seconds"%defaultSkinTime)
                        ret[meshShape] = thisRetData
                        continue
                else:
                    # If it is already skinned, add any missing influences from the
                    # weight data (SkinChunk or UberChunk) to it, so those weights
                    # can be properly applied later.
                    #
                    # But, adding these influences may not be in the same order
                    # as what was saved in the SkinChunk, need to reorder weight
                    # data later
                    skinClusterInfluenceNames = [dPath.fullPathName() for dPath in mFnSkinCluster.influenceObjects()]

                    if verbose:
                        print("\tCurrently skinned: Checking for SkinChunk influences it's missing and adding if needed (if they exist in the scene / created in an above step if missing)...")
                    newInfNames = [name for name in list(infNameData.values()) if name not in skinClusterInfluenceNames]

                    if newInfNames:
                        if selectVertsOnly:
                            raise Exception("selectVertsOnly=True, but it was found that the existing skinCluster would need to be modified with new influences, possibly undesirably.")
                        if verbose:
                            print("\t\tAdding Existings Influences to SkinCluster:")
                            for newInf in sorted(newInfNames):
                                print("\t\t\t%s"%newInf)
                        utils.addInfluences(mFnSkinCluster, newInfNames)
                        skinClusterInfluenceNames = [dPath.fullPathName() for dPath in mFnSkinCluster.influenceObjects()]
                    else:
                        if verbose:
                            print("\t\tNo new influences to add!")

                #-------------------------------------------------------------------
                #-------------------------------------------------------------------
                # Weight import logic:
                startSkinTime = time.time()
                # 0 = linear, 1 = dual quat, 2 = weight blended
                skinMethod = mc.getAttr('%s.skinningMethod'%mFnSkinCluster.name())
                # This will get filled with our skin import algos below, with
                # keys for "weights" and "blendWeights".  "blendghts" is only calcualted
                # / populated if the skinCluster is set to 'weight blended'.
                weightData = {}
                importVertPositions = None
                importVertNormals = []
                if importUsingPreDeformedPoints:
                    # Find the worldspace positions of our pre-deformed shape verts:
                    preDeformedshape = utils.getPreDeformedShape(meshShape)
                    preDeformedVertNames = ["%s.vtx[%s]"%(preDeformedshape, vid) for vid in importVertIds]
                    importVertPositions = np.array([mc.pointPosition(v, world=True) for v in preDeformedVertNames])
                    if filterByVertNormal:
                        importVertNormals = [om2.MVector(n) for n in utils.getVertNormals(preDeformedVertNames)]
                else:
                    # Use whatever is the current worldspace position for our verts:
                    importVertPositions = np.array([mc.pointPosition(v, world=True) for v in importVertNames])
                    if filterByVertNormal:
                        importVertNormals = [om2.MVector(n) for n in utils.getVertNormals(importVertNames)]

                if importFromUberChunk:
                    # Import based on uberChunk info
                    if verbose:
                        print("\tUberChunk Import:")
                    savedVertPositions = None
                    if importUsingPreDeformedPoints and hasattr(uberChunk, "vertPositionsPreDeformed"):
                        # Introduced in 1.1.0, so old saved data may not have this
                        # method/attr.
                        savedVertPositions = np.array(uberChunk.getVertPositions(preDeformed=True))
                        if verbose:
                            print("\t\tUsing 'pre-deformed' vert positions for the import in both what is stored in the UberChunk, and on the current mesh.")
                    else:
                        savedVertPositions = np.array(uberChunk.getVertPositions(preDeformed=False))
                        if verbose:
                            print("\t\tUsing the current worldspace positions for the import based on both what is stored in the UberChunk, and on the current mesh.")

                    allSavedWeights = uberChunk.getAllWeights() # ndarray
                    allSavedBlendWeights = []
                    if skinMethod == 2:
                        # Weight Blended
                        allSavedBlendWeights = uberChunk.getAllBlendWeights() # ndarray

                    allSavedVertNormals =  [om2.MVector(n) for n in uberChunk.getAllNormals()]

                    if fallbackSkinningMethod == "closestPoint":
                        if verbose:
                            print("\t\tImporting by 'Closest Point' on %s verts using '%s'..."%(numImportOntoVerts, closestPointFunc.__name__))
                        weightData = closestPointWeights(allSavedWeights, allSavedBlendWeights,
                                                         importVertPositions, savedVertPositions,
                                                         importVertNormals, allSavedVertNormals,
                                                         closestPointFunc=closestPointFunc,
                                                         filterByVertNormal=filterByVertNormal, vertNormalTolerance=vertNormalTolerance)
                        thisRetData["importMethod"] = "No Name Match (UberChunk) : Closest Point"

                    elif fallbackSkinningMethod == "closestNeighbors":
                        if verbose:
                            print("\t\tImporting by '%s Closest Neighbors Weights' on %s verts using '%s'..."%(closestNeighborCountStr, numImportOntoVerts, closestPointFunc.__name__))
                        weightData = closestNeighborsWeights(allSavedWeights, allSavedBlendWeights,
                                                             importVertPositions, savedVertPositions,
                                                             importVertNormals, allSavedVertNormals,
                                                             closestNeighborCount, closestNeighborDistMult,
                                                             closestPointFunc=closestPointFunc,
                                                             filterByVertNormal=filterByVertNormal, vertNormalTolerance=vertNormalTolerance)
                        thisRetData["importMethod"] = "No Name Match (UberChunk) : Nearest Neighbors"

                else:
                    if verbose:
                        print("\tSkinChunk Import:")

                    skinChunkMeshVertCount = skinChunk.getMeshVertCount()
                    #allSavedWeights is ndarray[x][y] where Each item (x, represents vert ids) is a
                    #sublist (y)  : The sublist are weights in relationship to the passed
                    #ininfluences list.  Ultimately, this was generated by utils.getWeights.
                    allSavedWeights = skinChunk.getAllWeights()
                    allSavedBlendWeights = skinChunk.getAllBlendWeights()
                    numSavedVerts = skinChunk.getNumVerts()

                    savedVertPositions = None
                    allSavedVertNormals = None
                    if importUsingPreDeformedPoints and hasattr(skinChunk, "vertPositionsPreDeformed"):
                        # Introduced in 1.1.0, so old saved data may not have this
                        # method/attr.
                        savedVertPositions = np.array(skinChunk.getVertPositions(preDeformed=True))
                        if filterByVertNormal:
                            allSavedVertNormals = [om2.MVector(n) for n in skinChunk.getAllNormals(preDeformed=True)]
                        if verbose:
                            print("\t\tUsing 'pre-deformed' vert positions for the import in both what is stored in the SkinChunk, and on the current mesh.")

                    else:
                        savedVertPositions = np.array(skinChunk.getVertPositions(preDeformed=False))
                        if filterByVertNormal:
                            # Need to also sorted by pre-deformed or worldspace:
                            allSavedVertNormals = [om2.MVector(n) for n in skinChunk.getAllNormals(preDeformed=False)]
                        if verbose:
                            print("\t\tUsing the current worldspace positions for the import based on both what is stored in the SkinChunk, and on the current mesh.")

                    if meshVertCount == skinChunkMeshVertCount:
                        # Import in by vert id... maybe?  Do the vert orders match?
                        # Calc if our neighbor vert ids match:
                        storedVertNeightbors = skinChunk.getVertNeighborSamples()
                        neighborsMatch = True
                        if storedVertNeightbors:
                            currentVertNeightbors = utils.getVertNeighborSamples(meshShape, skinChunk.getNumNeighborSamples())
                            for key in storedVertNeightbors:
                                storedNeighbors = storedVertNeightbors[key]
                                currentNeighbors = currentVertNeightbors[key]
                                if storedNeighbors != currentNeighbors:
                                    neighborsMatch = False
                                    break

                        if neighborsMatch:
                            # Neighbord vert IDs match, load by id!  The fastest!! :)

                            # No post smooth when loading by vert ID, since we
                            # want to preserve the original weights.
                            doPostSmooth = 0
                            savedVertIds = skinChunk.getVertIds()
                            newImportVertIds = []
                            newSavedWeights = []
                            newSavedBlendWeights = []
                            dataOverride = False
                            if set(savedVertIds) != set(importVertIds):
                                dataOverride = True
                                # If the IDs of verts being imported onto is different
                                # That then number saved:  Modify what's being imported
                                # onto to only be the intersection of those verts,
                                # and the ones that were saved.
                                if verbose:
                                    print("\t\tSkinChunk/current mesh vert counts/neighbors match: Importing by 'vert ID' *but*:")
                                    print("\t\tThe vert IDs of the saved weight list (%s) is different from what is being imported on (%s):  Updating the list of 'imported verts IDs' to match the saved weight list (%s)."%(len(savedVertIds), len(importVertIds), len(savedVertIds)))
                                for i,svid in enumerate(savedVertIds):
                                    if svid in importVertIds:
                                        newSavedWeights.append(allSavedWeights[i])
                                        if len(allSavedBlendWeights):
                                            newSavedBlendWeights.append(allSavedBlendWeights[i])
                                        newImportVertIds.append(svid)
                                newSavedWeights = np.array(newSavedWeights)
                                # And now override what was originally passed in:
                                importVertIds = newImportVertIds
                                importVertNames = ["%s.vtx[%s]"%(meshShape, vid) for vid in importVertIds]
                                numImportOntoVerts = len(importVertIds)
                            else:
                                newSavedWeights = allSavedWeights
                                newSavedBlendWeights = allSavedBlendWeights

                            weightData["weights"] = newSavedWeights
                            if verbose and not dataOverride:
                                print("\t\tSkinChunk/current mesh vert counts/neighbors match: Importing by 'vert ID' on %s/%s verts..."%(numSavedVerts, numImportOntoVerts))

                            if skinMethod == 2:
                                # only compute if we're applying weight-blended skinning:
                                weightData["blendWeights"] = newSavedBlendWeights
                            else:
                                weightData["blendWeights"] = []

                            if foundSkinChunkNameMatch:
                                thisRetData["importMethod"] = "Name Match (SkinChunk) : Vert ID & Order Match"
                            else:
                                thisRetData["importMethod"] = "Name Mismatch (SkinChunk) : Vert ID & Order Match"

                            #!!! But what if you're only importing on a subset?
                            # What happens to the verts not being udpated?
                            # If 'unbind first' is false, do nothing, since they
                            # alreay have skinnnig.  But if 'unbind first' is True,
                            # then interpolate the weights on the unselected verts
                            # based on the weights just imported.
                            # Right now, it's just using the default skinning applied
                            # above... Maybe something fancier in the future?

                        else:
                            # Names and vert count match, but neighbor IDs (order) don't:
                            if fallbackSkinningMethod == "closestPoint":
                                # Neighbord IDs don't match, load by closest point.
                                if verbose:
                                    print("\t\tSkinChunk/current mesh vert counts match:, but neighbor IDs don't: Importing by 'Closest Point' using '%s' on %s verts..."%(closestPointFunc.__name__, numImportOntoVerts))
                                weightData = closestPointWeights(allSavedWeights, allSavedBlendWeights,
                                                                 importVertPositions, savedVertPositions,
                                                                 importVertNormals, allSavedVertNormals,
                                                                 closestPointFunc=closestPointFunc,
                                                                 filterByVertNormal=filterByVertNormal, vertNormalTolerance=vertNormalTolerance)
                                thisRetData["importMethod"] = "Name Match (SkinChunk) : Closest Point : Vert order mismatch."

                            elif fallbackSkinningMethod == 'closestNeighbors':
                                if verbose:
                                    print("\t\tSkinChunk/current mesh vert counts match:, but neighbor IDs don't: Importing by '%s Closest Neighbors Weights' using '%s' on %s verts..."%(closestNeighborCountStr, closestPointFunc.__name__, numImportOntoVerts))
                                weightData = closestNeighborsWeights(allSavedWeights, allSavedBlendWeights,
                                                                  importVertPositions, savedVertPositions,
                                                                  importVertNormals, allSavedVertNormals,
                                                                  closestNeighborCount, closestNeighborDistMult,
                                                                  closestPointFunc=closestPointFunc,
                                                                  filterByVertNormal=filterByVertNormal, vertNormalTolerance=vertNormalTolerance)
                                thisRetData["importMethod"] = "Name Match (SkinChunk) : Closest Nearest Neighbor : Vert order mismatch."

                    else:
                        # Mesh names match, but not vert count: import by our fallback method.
                        if fallbackSkinningMethod == "closestPoint":
                            if verbose:
                                print("\t\tFound mesh name match, but vert count doesn't: Importing by 'Closest Point' using '%s' on %s verts..."%(closestPointFunc.__name__, numImportOntoVerts))
                            weightData = closestPointWeights(allSavedWeights, allSavedBlendWeights,
                                                             importVertPositions, savedVertPositions,
                                                             importVertNormals, allSavedVertNormals,
                                                             closestPointFunc=closestPointFunc,
                                                             filterByVertNormal=filterByVertNormal, vertNormalTolerance=vertNormalTolerance)
                            thisRetData["importMethod"] = "Name Match (SkinChunk) : Closest Point : Vert count mismatch"

                        elif fallbackSkinningMethod == 'closestNeighbors':
                            if verbose:
                                print("\t\tFound mesh name match, but vert count doesn't: Importing by '%s Closest Neighbors Weights' using '%s' on %s verts..."%(closestNeighborCountStr, closestPointFunc.__name__, numImportOntoVerts))
                            weightData = closestNeighborsWeights(allSavedWeights, allSavedBlendWeights,
                                                                 importVertPositions, savedVertPositions,
                                                                 importVertNormals, allSavedVertNormals,
                                                                 closestNeighborCount, closestNeighborDistMult,
                                                                 closestPointFunc=closestPointFunc,
                                                                 filterByVertNormal=filterByVertNormal, vertNormalTolerance=vertNormalTolerance)
                            thisRetData["importMethod"] = "Name Match (SkinChunk) : Closest Nearest Neighbor : Vert count mismatch."

                if not selectVertsOnly:

                    #--------------------

                    #------------
                    # Apply weights!
                    # When the code was first authored, up until 1.0.10, there was
                    # a scripted plugin wrappering the mFnSkinCluster.setWeights
                    # call, to support undo: This caused a number of annoying issues,
                    # around dealing with relative imports in that code, and not
                    # being able to obfuscate it via PyArmor.  Later, the below
                    # hack was found on how to hijack Maya's undo queue, and the
                    # whole scripted plugin was deprecated.

                    # MDagPathArray of our influences:
                    infDags = mFnSkinCluster.influenceObjects()

                    skinClusterInfLeafNames = [name.split("|")[-1] for name in skinClusterInfluenceNames]
                    # Make sure the weight values are listed in the same order as
                    # the skinCluster, and not that of the SkinChunk:
                    weights = utils.transposeWeights(weightData["weights"],
                                                     skinChunkInfNames,
                                                     skinClusterInfLeafNames )
                    blendWeights = []
                    if skinMethod == 2:
                        blendWeights = utils.transposeWeights(weightData["blendWeights"],
                                                              skinChunkInfNames,
                                                              skinClusterInfLeafNames )

                    skinClustName = mFnSkinCluster.name()
                    utils.unlockInfluences(skinClustName)

                    # Setup our API command call args:
                    #
                    # Pre-populate with a bunch of zeros.  Will be populated
                    # next with the index of each influence
                    infIndexes = om2.MIntArray(len(infDags), 0)
                    for x in range(len(infDags)):
                        infIndexes[x] = int(mFnSkinCluster.indexForInfluenceObject(infDags[x]))
                    # MDagPath for the mesh shape:
                    meshDagPath = utils.getMDagPath(meshShape)
                    # An MObject storing the vert IDs for each vert being imported on
                    importVertexCompObj = utils.getMObjectForVertIndices(importVertNames) # allMeshVertNames)

                    # One big array for each vertex, in order, of it's weights relative
                    # to each influence.
                    # To get that, we need to 'unpack' our current weights 'list of sublists':
                    weights = [list(items) for items in weights]
                    chained = [item for item in itertools.chain(*weights)]
                    arrayWeights = om2.MDoubleArray([float(item) for item in chained])

                    mc.undoInfo(openChunk=True, chunkName="setWeights undoHack")
                    try:
                        #----------------------------------------
                        # Hack the undo queue: Put in dummy values.  If you 'undo'
                        # this command, Maya thinks you're undoing the next line,
                        # which will restore the previous weights.
                        inf = infDags[0].fullPathName()
                        mc.skinPercent(skinClustName, importVertNames, transformValue=[(inf, 1.0)]) # allMeshVertNames

                        #----------------------------------------
                        # Set the weights fast via the API
                        #
                        # Sometimes calling MFnSkinCluster.setWeights will raise an error:
                        #
                        # '(kInvalidParameter): Object is incompatible with this method'
                        #
                        # Debugging error, found this code, just a note of something
                        # doing someting similar to here:
                        # https://github.com/pmolodo/pmHeatWeight/blob/master/src/PM_heatWeight.py
                        #
                        # I've tried to solve the error a variety of ways without
                        # success.  For example:
                        # 1. Having a simple repro case, saving it as .ma, 'fixing'
                        #    it in another ma file and diffing them:  Unable to
                        #    find noticable differnces.
                        # 2. Wholesale copying the skinCluster creation code from
                        #    the 'good' ma to the 'bad' ma:  Bug still present.
                        normalize = False
                        returnOldWeights = False
                        # https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=Maya_SDK_py_ref_class_open_maya_anim_1_1_m_fn_skin_cluster_html
                        # * shape       (MDagPath) - object being deformed by the skinCluster
                        # * components   (MObject) - the components to set weights on
                        # * influences (MIntArray) - physical indices of several influence objects.
                        # * weights (MDoubleArray) - weights to be used with several influence objects.
                        mFnSkinCluster.setWeights(meshDagPath, importVertexCompObj, infIndexes, arrayWeights, normalize, returnOldWeights)

                        if skinMethod == 2:
                            # Weight Blended only:
                            # Hack the undo queue: Put in dummy values.
                            # Why doesn't the skinPercent command support this?
                            # calling to setAttr this many times sucks.
                            for vid in importVertIds:
                                mc.setAttr(f"{skinClustName}.blendWeights[{vid}]", 0)
                            # Set the weights fast via the API
                            arrayBlendWeights = om2.MDoubleArray(blendWeights)
                            mFnSkinCluster.setBlendWeights(meshDagPath, importVertexCompObj, arrayBlendWeights)
                        thisRetData["success"] = True
                    except RuntimeError as e:
                        print(f"\t\t\tMaya Runtime Error: '{e}'")
                        if not unskinFirst:
                            print("\t\t\tBased on the above error:  There's an issue where some mesh with existing skinCluster data reject new weights being applied.  Two ways to fix:")
                            print("\t\t\t\t#1: Auto: Select the mesh, and use the 'Extra' tab in the Skinner window, and access 'Auto-Fix Broken skinCluster' tool, to auto-export & reimport the mesh's skinning to rebuild the skinnCluster.  Then, re-run this tool to get the new skinning applied.")
                            print("\t\t\t\t#2: Manually:  The 'unskinFirst' arg is currently set to False : Changing this to True and trying again can fix this error, since it will delete & rebuild the skinCluster in the process.  Only do this if you're reimporting skinning on a whole mesh, not a subset of verts.")
                        thisRetData["success"] = False
                    finally:
                        mc.undoInfo(closeChunk=True, chunkName="setWeights undoHack")

                    #--------------------
                    # Post Smoothing

                    # We should only do smoothing if we're going form a low-res
                    # source (the SkinChunk data) to a high-res target (our
                    # mesh) : If it's the reverse, then smoothing can actually
                    # make it look worse.
                    numChunkPoints = theChunk.getMeshVertCount()
                    if meshVertCount < numChunkPoints and thisRetData["success"] == True:
                        if doPostSmooth:
                            print(f"\t\tPost-smoothing was enabled ({doPostSmooth} steps), but the vert count of the mesh being imported onto ({meshVertCount}) is less than that of points stored in the SkinChunk ({numChunkPoints}): Smoothing is generally only needed, and only provides good results, if the number of points in the SkinChunk is *less* than that of the mesh.")
                        doPostSmooth = 0

                    if doPostSmooth and thisRetData["success"] == True:
                        startSmoothTime = time.time()
                        # We only want to smooth verts that don't have a corresponding
                        # worldspace position match based on the SkinChunk being
                        # used.  Since if they do, those weights were probably
                        # loaded on nearly 1:1 values, and we don't want to change
                        # that.
                        smoothMe = []
                        comparePoints = [om2.MPoint(point) for point in theChunk.getVertPositions()]
                        #comparePoints = np.array( theChunk.getVertPositions() )
                        for importVertName in importVertNames:
                            doSmooth = True
                            # Brute Force sample : .07 seconds
                            thisPoint = om2.MPoint(mc.pointPosition(importVertName, world=True))
                            for comparePoint in comparePoints:
                                if thisPoint.distanceTo(comparePoint) < .01:
                                    doSmooth = False
                                    break

                            # KDTree fanciness sample : .35 seconds.  HUM, am I doing it wrong?
                            #thisPoint = np.array(mc.pointPosition(importVertName, world=True))
                            # global gMultiThread
                            #workers = 1 # The KDTree.query default : Use 1 processor.
                            #if gMultiThread:
                                #workers = -1 # use all'dem
                            #distances, indexes = KDTree(comparePoints).query(thisPoint, distance_upper_bound=.01, workers=workers)
                            #if distances:
                            if doSmooth:
                                smoothMe.append(importVertName)

                        # This is *super gross* (picking verts), but if you want
                        # to smooth only a subset, this is the only way that I've
                        # found the skinCluster command lets you do it :-S
                        if smoothMe:
                            mc.select(smoothMe)
                            obeyMaxInfluences = mc.getAttr(f"{mFnSkinCluster.name()}.maintainMaxInfluences")
                            try:
                                # This command will smooth verts who's weights
                                # are 25% different (or more) from those around
                                # them.  Basically everything in the smoothList.
                                mc.skinCluster(mFnSkinCluster.name(), edit=True,
                                               smoothWeights=postSmoothWeightDiff,
                                               smoothWeightsMaxIterations=doPostSmooth,
                                               obeyMaxInfluences=obeyMaxInfluences)
                                if verbose:
                                    endSmoothTime = time.time() - startSmoothTime
                                    print("\t\tPost-smoothed skinning on %s/%s verts with %s steps using a weight difference threshold of greater than %s percent in %.2f seconds."%(len(smoothMe),  len(importVertNames), postSmoothWeightDiff, postSmoothWeightDiff*10, endSmoothTime))
                            except RuntimeError as e:
                                print("\t\t\t%s"%e)
                        elif verbose:
                            endSmoothTime = time.time() - startSmoothTime
                            print("\t\tFound no verts (out of %s) to smooth in %.2f seconds: They all have worldspace position matches with imported data."%(len(importVertNames), endSmoothTime))

                    mc.skinCluster(mFnSkinCluster.name(), edit=True, forceNormalizeWeights=True)

                else:
                    selectMe.extend(importVertNames)

                skinTimeTotal = time.time() - startSkinTime

                if skinTimeTotal == 0:
                    skinTimeTotal = 0.0001
                if verbose:
                    if thisRetData["success"] == False:
                        # the section where the error happens already prints
                        # error info.
                        #print("\tEncountered errors when setting skin weights, see above ^")
                        pass
                    else:
                        vertsPerSec = len(importVertIds) / skinTimeTotal
                        if selectVertsOnly:
                            print("\tSelected verts (no skinning) in %.2f seconds: %s verts per second."%(skinTimeTotal, int(vertsPerSec)))
                        else:
                            print("\tImported on %s verts in %.2f seconds: %s verts per second."%(len(importVertIds), skinTimeTotal, int(vertsPerSec)))
                thisRetData["totalTime"] = skinTimeTotal
                thisRetData["newInfluences"] = newInfs

                ret[meshShape] = thisRetData

        if selectMe:
            mc.select(selectMe)

    finally:
        mc.undoInfo(closeChunk=True, chunkName="setWeights")
        timeEnd = time.time()

    if verbose:
        timeTotal = timeEnd - timeStart
        if verbose:
            print("#----------------------------------------------------------")

            if thisRetData["success"]:
                if selectVertsOnly:
                    om2.MGlobal.displayInfo("Vert Selection Complete (no skinning)%s: Selected all verts in %.3f seconds"%(timeTotal))
                else:
                    om2.MGlobal.displayInfo("Weight Import Complete: Set all weights in %.3f seconds"%(timeTotal))
            else:
                if selectVertsOnly:
                    om2.MGlobal.displayError("Vert Selection Complete (no skinning), but encountered errors (see above ^): Selected verts in %.3f seconds"%(timeTotal))
                else:
                    om2.MGlobal.displayError("Weight Import Complete, but encountered errors (see above ^): Set weights in %.3f seconds"%(timeTotal))


    return ret

#-----------------------
# Main tools

def exportSkin(items=None, filePath=None, verbose=True, vcExportCmd=None, vcDepotRoot=None,
               setToBindPose=False) -> (bool, None):
    r"""
    For the selected/provided mesh, export their SkinChunks.  This is a wrapper
    around generateSkinChunks and exportSkinChunks.  The main export point interface.

    If you're using Perforce as your version control software, please read important
    notes in the docstring of exportSkinChunks about it.

    Parameters:
    items : None/list : Default None : If None, use the active selection (mesh,
        poly components, joints). Otherwise act on the provided list of mesh/verts.
        Note, that in either case, the tool will work on the full recursive hierarchy
        of what is provided, finding all child mesh shape nodes. For example, pass
        in a single root group/transform, and it will act on all child mesh.  Pass
        in a single vert, and that's all it'll work on.  Mix and match!
    filePath : string/None : If string, save it to that location.  If None,
        open an file browser for the user to choose.  If the file/dir doesn't yet
        exist, the tool will create that directory tree.  It is presumed this
        file is writable, if it exists.
    verbose : bool : Default True : Print the results of the operation?
    vcExportCmd : None / string : Default None : See docstring of exportSkinChunks.
    vcDepotRoot : None / string : Default None : See docstring of exportSkinChunks.
    setToBindPose : bool : Default False : Passed directly to generateSkinChunks,
        see its docstring for details.

    Return : bool / None : If any errors, return False.  If export successfull,
        reurn True.  If the operation is canceled, return None.
    """
    startTime = time.time()
    #--------------------------------
    # Begin pre-save validation :

    meshShapeVertIds = utils.getMeshVertIds(items=items)

    if verbose:
        print("#----------------------------------------------------------")
        print("Skinner Exporting SkinChunks....")

    if not meshShapeVertIds:
        om2.MGlobal.displayError("Skinner: No mesh is selected or provided to export skin on.")
        return False

    # Make sure all the selected mesh is skinned.
    unskinned = []
    for m in meshShapeVertIds.keys():
        sc = utils.getMFnSkinCluster(m)
        if not sc:
            unskinned.append(m)
    if unskinned:
        om2.MGlobal.displayError("%s mesh are unsknined: Unable to save skinner weights: %s"%(len(unskinned), unskinned))
        return False

    if filePath:
        if not filePath.endswith(".%s"%EXT):
            om2.MGlobal.displayError("Skinner: The 'filePath' must end with a '.%s' extension, recieved: '%s'"%(EXT, filePath))
            return False
        weightDir = os.path.dirname(filePath)
        if not os.path.isdir(weightDir):
            os.makedirs(weightDir)
    else:
        startDir = ""
        if mc.optionVar(exists=OV_LAST_SAVE_PATH):
            startDir = mc.optionVar(query=OV_LAST_SAVE_PATH)
            if not os.path.isdir(startDir):
                startDir = ""
        weightPaths = mc.fileDialog2(caption="Export Skin File", fileMode=0, okCaption="Export",
                                    fileFilter="Skinner Files: (*.%s)"%EXT, startingDirectory=startDir)
        if weightPaths:
            filePath = weightPaths[0]
            weightDir = os.path.dirname(filePath)
            mc.optionVar(stringValue=[OV_LAST_SAVE_PATH, weightDir])
        else:
            return None

    #if os.path.isfile(filePath):
        #if not  os.access(filePath, os.W_OK):
            #om2.MGlobal.displayError("Skinner: The provided file is read-only: '%s'"%filePath)
            #return False

    #--------------------------------
    # Validation complete, save!
    try:
        skinChunks = generateSkinChunks(meshShapeVertIds, setToBindPose=setToBindPose, verbose=verbose)
    except Exception as e:
        print(e)
        om2.MGlobal.displayError("Encountered errors trying to generate SkinChunk data, see above ^")
        return False

    if not skinChunks:
        return None
    exportSkinChunks(filePath, skinChunks, verbose=verbose, vcExportCmd=vcExportCmd, vcDepotRoot=vcDepotRoot)

    if verbose:
        totalTime = time.time() - startTime
        om2.MGlobal.displayInfo("Skinner Export complete in %.2f seconds"%totalTime)

    return True

def importSkin(items=None, filePaths=None, verbose=True, printOverview=True, printOverviewMode="byImportType",
               **kwargs) -> (dict,bool,None):
    r"""
    Import the skin on the provided mesh.  This is an wrapper around importSkinChunks
    & setWeights.  The main import point interface.

    Parameters:
    items : None/list : Default None : If None, use the active selection (mesh,
        poly components, joints). Otherwise act on the provided list of mesh/verts.
        Note, that in either case, the tool will work on the full recursive hierarchy
        of what is provided, finding all child mesh shape nodes. For example, pass
        in a single root group/transform, and it will act on all child mesh.  Pass
        in a single vert, and that's all it'll work on.  Mix and match!
    filePaths : list/string/None : If list/string, load from that location.  If None,
        open an file browser for the user to choose.
    verbose : bool : Default True : Print detailed results?
    printOverview : bool : Default True : Print a condenced overview of the results?
       Regardless of the printOverviewMode used, they'll be collected by successes
       and failures.
    printOverviewMode : string : Default "byImportType" : If printOverview=True,
        what type of overview to print?  Also supports "byMesh".
        * "byImportType" : This will collect all the mesh into 'import type' buckets,
            like 'Vert ID & Order Match', 'Single Influence', etc.
        * "byMesh" : This lists each mesh in order, and what import method was used.
    kwargs : Any additional keyword:args that should be passed to setWeights,
        based on it's parameters/arguments, asside from what is above.

    Return : dict / None : If any errors, return False.  If load was successfull,
        reurn a dict, which is the return from setWeights.  If the operation is
        canceled, return None.
    """
    sel = mc.ls(selection=True)
    startTime = time.time()
    meshShapeVertIds = utils.getMeshVertIds(items=items)
    if not meshShapeVertIds:
        om2.MGlobal.displayError("Skinner: No mesh/verts are selected or provided to import on")
        return False

    if filePaths:
        if not isinstance(filePaths, (list,tuple)):
            filePaths = [filePaths]
        for filePath in filePaths:
            if not filePath.endswith(".%s"%EXT):
                om2.MGlobal.displayError("Skinner: The 'filePath' must end with a '.%s' extension, recieved: '%s'"%filePath)
                return False
    else:
        startDir = ""
        if mc.optionVar(exists=OV_LAST_SAVE_PATH):
            startDir = mc.optionVar(query=OV_LAST_SAVE_PATH)
            if not os.path.isdir(startDir):
                startDir = ""
        filePaths = mc.fileDialog2(caption="Import Skin File", fileMode=4, okCaption="Import",
                                    fileFilter="Skinner Files: (*.%s)"%EXT, startingDirectory=startDir)
        if not filePaths:
            return None

    skinChunks = importSkinChunks(filePaths, verbose=verbose)
    # results = dict, keys for mesh shapes, values are subdicts:
    # "totalTime":seconds,
    # "importMethod":"the method used",
    # "success":bool, where it's True if the weights were set, and False if
    #     something went wrong.
    try:
        results = setWeights(items, skinChunks=skinChunks, verbose=verbose, **kwargs)
    except Exception as e:
        tb = sys.exc_info()[2]
        tbExtract = traceback.extract_tb(tb)
        tbList = traceback.format_list(tbExtract)
        print ("Traceback:")
        for line in tbList:
            print (line.rstrip())

        print("Exception:", e)
        om2.MGlobal.displayError("Skinner: Encountered an error when setting weights, see above ^")
        return False

    anyFailures = False
    if printOverview:
        totalComputeTime = time.time() - startTime
        print("\n#----------------------------------------------------------")
        print("Skinner Import Overview:")

        if printOverviewMode == "byImportType":
            successTypeDict = {}
            failTypeDict = {}
            for meshShape in sorted(results):
                importData = results[meshShape]
                totalTime = importData["totalTime"]
                importMethod = importData["importMethod"]
                success = importData["success"]
                # Sort out data into success/fail buckets:
                if success:
                    if importMethod not in successTypeDict:
                        successTypeDict[importMethod] = [ [meshShape, totalTime] ]
                    else:
                        successTypeDict[importMethod].append( [meshShape, totalTime] )
                else:
                    anyFailures = True
                    if importMethod not in failTypeDict:
                        failTypeDict[importMethod] = [ [meshShape, totalTime] ]
                    else:
                        failTypeDict[importMethod].append([meshShape, totalTime])

            if successTypeDict:
                print("    Successfull Imports:")
                for importMethod in sorted(successTypeDict):
                    print("        Import Type: '%s'"%importMethod)
                    for meshData in successTypeDict[importMethod]:
                        print("            %s : %.2f Seconds"%(meshData[0], meshData[1]))
            if failTypeDict:
                print("    Failed Imports:")
                for importMethod in sorted(failTypeDict):
                    print("        Import Type: '%s'"%importMethod)
                    for meshData in failTypeDict[importMethod]:
                        print("            %s : %.2f Seconds"%(meshData[0], meshData[1]))

        elif printOverviewMode == "byMesh":
            successData = []
            failData = []
            for meshShape in sorted(results):
                importData = results[meshShape]
                totalTime = importData["totalTime"]
                importMethod = importData["importMethod"]
                success = importData["success"]
                if success:
                    successData.append("        %s"%meshShape)
                    successData.append("            Import Method : %s"%importMethod)
                    successData.append("            Total Time : %.2f Seconds"%totalTime)
                else:
                    anyFailures = True
                    failData.append("        %s"%meshShape)
                    failData.append("            Import Method : %s"%importMethod)
                    failData.append("            Total Time : %.2f Seconds"%totalTime)
            if successData:
                print("    Import Successes:")
                for success in successData:
                    print(success)
            if failData:
                print("    Import Failures:")
                for fail in failData:
                    print(fail)


        if not anyFailures:
            print("    Import completed in %.3f seconds"%totalComputeTime)
            om2.MGlobal.displayInfo("Successfully imported all Skinner data, see 'Import Overview' above ^")
        else:
            om2.MGlobal.displayError("Expereinced Skinner import errors, see 'Import Overview' above ^")

    elif verbose:
        if not anyFailures:
            print("Import completed in %.3f seconds"%totalComputeTime)
        else:
            om2.MGlobal.displayWarning("Expereinced Skinner import errors, see 'Import Overview' above ^")

    resetSel = True
    if "selectVertsOnly" in kwargs:
        if kwargs["selectVertsOnly"]:
            resetSel = False

    if resetSel:
        if sel:
            mc.select(sel)
        else:
            mc.select(clear=True)

    return results

#------------

def exportTempSkin(items=None, verbose=True, tempFilePath=TEMP_FILE_PATH, **kwargs):
    r"""
    Export SkinChunks to the temp file.  Can be read back into this Maya instance,
    or any other open Maya instance.  Will use the default args to exportSkin
    unless overridden by kwargs.

    Parameters:
    items : None/list : Default None : If None, use the active selection (mesh,
        poly components, joints). Otherwise act on the provided list of mesh/verts.
        Note, that in either case, the tool will work on the full recursive hierarchy
        of what is provided, finding all child mesh shape nodes. For example, pass
        in a single root group/transform, and it will act on all child mesh.  Pass
        in a single vert, and that's all it'll work on.  Mix and match!
    verbose : bool : Default True : Print results?
    tempFilePath : string : Default TEMP_FILE_PATH : Where should this temp skinning
        be exported?  Downstream code will auto-create this dir if it doesn't exist.
    kwargs : Any additional keyword:args that should be passed to exportSkin,
        based on it's parameters/arguments, asside from what is above.  Note, the
        'filePaths' arg wil be auto-popped since we're overriding it here.
    """
    if not items:
        if not utils.getMeshVertIds():
            om2.MGlobal.displayError("skinner : No mesh provided, can't export temp weights.")
            return

    if os.path.isfile(TEMP_FILE_PATH):
        os.remove(TEMP_FILE_PATH)
    if "filePaths" in kwargs:
        kwargs.pop("filePaths")
    exportSkin(items=items, filePath=tempFilePath, verbose=verbose, **kwargs)

def importTempSkin(items=None, verbose=True, tempFilePath=TEMP_FILE_PATH, **kwargs):
    r"""
    Import SkinChunks from the temp file and apply their skinning.  Presumed
    exportTempWeights was ran first. Can be read back into this Maya instance,
    or any other open Maya instance.  Will use the default args to importSkin
    unless overridden by kwargs.

    Parameters:
    items : None/list : Default None : If None, use the active selection (mesh,
        poly components, joints). Otherwise act on the provided list of mesh/verts.
        Note, that in either case, the tool will work on the full recursive hierarchy
        of what is provided, finding all child mesh shape nodes. For example, pass
        in a single root group/transform, and it will act on all child mesh.  Pass
        in a single vert, and that's all it'll work on.  Mix and match!
    verbose : bool : Default True : Print results?
    tempFilePath : string : Default TEMP_FILE_PATH : Where should this skinning
        be imported from?
    kwargs : Any additional keyword:args that should be passed to setWeights,
        based on it's parameters/arguments, asside from what is above.  Note, the
        'filePaths' arg wil be auto-popped since we're overriding it here.
    """
    if not items:
        if not utils.getMeshVertIds():
            om2.MGlobal.displayError("skinner : No mesh provided, can't import temp weights.")
            return

    if not os.path.isfile(tempFilePath):
        om2.MGlobal.displayError("skinner : No 'temp' weight file to import from, expected to find here: '%s'"%(tempFilePath))
        return
    if "filePaths" in kwargs:
        kwargs.pop("filePaths")
    importSkin(items=items, filePaths=tempFilePath, verbose=verbose, printOverview=verbose, **kwargs)

def regenrateSkinCluster(items=[], verbose=True):
    """
    This is provided to work around a bug that can happen when trying to import
    skinning on to mesh/skinCluster data that wasn't made by this tool.  Inside
    of the setWeights function, an exception can be raised:
    '(kInvalidParameter): Object is incompatible with this method'
    An easy workaround is to regenerate that skinCluster using this tool.  So this
    function simply wrappers those steps:
    * For the provided mesh (not verts, since it needs to unbind the mesh / delete
        the existing skinCluster in the process):
    * Export temp skinning.
    * Reimport temp skinning.

    Parameters:
    items : list : default empty list : If not provided, the current selection is
        used.  Only supports mesh shapes, and transforms with mesh shapes.
    verbose : bool : Default True : Print verbose results.
    """
    mesh = []
    if not items:
        items = mc.ls(selection=True, long=True, flatten=True)
        if not items:
            om2.MGlobal.displayError("Please select one or more mesh.")
            return

    for item in items:
        if '.' in item:
            om2.MGlobal.displayError("Please select only mesh, not components.")
            return
        if not mc.objectType(item) in ("transform", "mesh"):
            om2.MGlobal.displayError(f"Please select only mesh, '{item}' is '{mc.objectType(item)}'")
            return
        mesh.append(utils.getMeshShape(item))

    if verbose:
        om2.MGlobal.displayInfo("")
        om2.MGlobal.displayInfo(f"Begin SkinCluster data regenration on {len(mesh)} mesh:")

        om2.MGlobal.displayInfo("")

    tempFilePath = os.path.join(TEMP_DIR, TEMP_FILE_REGEN)
    exportTempSkin(items=mesh, verbose=verbose, tempFilePath=tempFilePath)

    importTempSkin(items=mesh, verbose=verbose, tempFilePath=tempFilePath,
                   unskinFirst=True, importUsingPreDeformedPoints=False, setToBindPose=True)

    if verbose:
        om2.MGlobal.displayInfo("")
        om2.MGlobal.displayInfo(f"SkinCluster data regenerated on the provided {len(mesh)} mesh.  See details above ^")


#---------------------------------------------------------------------------

def test() -> bool:
    r"""
    Run the skinner test suite:
    * Prompt the user to create a new scene.
    * Create three joints.
    * Create poly plane 'A' with 1x12 subdivisions.
    * Create as simple poly cube at the position of the 2nd joint.
    * Skin the plane to the joints with some nice smooth weights.
    * Skin the cube to the end joint 100%.
    * Export those weights to a temp weight file.
    * Delete the previously created joint chain:  Rely on the tool to regenerate
        them during import.
    * Delete the poly plane 'A', and rebuild it.
    * Create poly plane 'B' with 2x24 subdivisions:
        Completely different topo than plane A.
    * Import the temp weights onto planes A&B + cube, using the default import
        options.
    * Select the 2nd joint, so the user can easily rotate it and see the results.

    Return : True
    """
    result = mc.confirmDialog(title="Confirm",
                              message="Run the 'skinner test suite?'\n\nNote:  This will use whatever your existing 'Skin -> Bind Skin -> Options' are as skinning defaults.\n\nThis will create a new Maya file: Continue?",
                              button=["Yes", "No"])
    if result == "No":
        return
    print("#--------------------------------------------")
    print("skinner test() : Begin Test Suite")

    mc.file(newFile=True, force=True)
    print("skinner test() : Created new scene.")

    mc.select(clear=True)
    j1 = mc.joint(position=(0,5,0))
    j2 = mc.joint(position=(0,0,0))
    j3 = mc.joint(position=(0,-5,0))
    joints = [j1, j2, j3]
    print("skinner test() : Created joint chain: %s"%joints)

    tfPlaneA, polyPlaneA = mc.polyPlane(width=1, height=12, axis=(0,0,1),
                                        subdivisionsX=1, subdivisionsY=12, name="planeA")
    print("skinner test() : Created: '%s' with 1x12 subdivisions."%tfPlaneA)
    tfCubeA, polyCubeA = mc.polyCube(name="cubeA")
    mc.setAttr('%s.translateY'%tfCubeA, -8)
    print("skinner test() : Created: '%s'."%tfCubeA)

    mc.skinCluster(joints, tfPlaneA, dropoffRate=5, maximumInfluences=3, toSelectedBones=True)
    print("skinner test() : Skinned '%s' 'smoothly' to %s."%(tfPlaneA, joints))

    mc.skinCluster(j3, tfCubeA, dropoffRate=10.0, maximumInfluences=1, toSelectedBones=True)
    print("skinner test() : Skinned '%s' 100 percent to %s."%(tfCubeA, j2))

    tempExportPath = "C:/temp/maya/skinner/tempExport.%s"%EXT
    print("skinner test() : Begin test weight export to : %s..."%tempExportPath)
    #meshShapeVertIds = utils.getMeshVertIds(items=[tfPlaneA, tfCubeA])
    exportSkin(items=[tfPlaneA, tfCubeA], filePath=tempExportPath, verbose=True)

    print("skinner test() : Printing saved/loaded SkinChunk data:\n")
    printWeightFile(tempExportPath, infListSlice=[0,10])

    print("skinner test() : Deleted the joints: %s"%joints)
    mc.delete(joints)

    print("skinner test() : Deleted %s"%tfPlaneA)
    mc.delete(tfPlaneA)

    tfPlaneA, polyPlaneA = mc.polyPlane(width=1, height=12, axis=(0,0,1),
                                        subdivisionsX=1, subdivisionsY=12, name="planeA")
    print("skinner test() : Re-created: '%s' with 1x12 subdivision on each axis."%tfPlaneA)

    tfPlaneB, polyPlaneB = mc.polyPlane(width=1, height=12, axis=(0,0,1),
                                        subdivisionsX=8, subdivisionsY=120, name="planeB")
    mc.setAttr('%s.translateZ'%tfPlaneB, .1)
    print("skinner test() : Created: '%s' with 8x120 subdivision on each axis."%tfPlaneB)

    reskin = [tfPlaneA, tfCubeA, tfPlaneB]
    print("skinner test() : Begin test weight import on %s, with default import args...\n"%(reskin))
    # get better results in this example with postSmoothWeightDiff=0.1, intead of .25
    importSkin(items=reskin, filePaths=tempExportPath, verbose=True, postSmoothWeightDiff=.01)

    mc.select(j2)
    print("\n#--------------------------------------------")
    om2.MGlobal.displayInfo("skinner test() : Test suite complete, see results above ^^:  Rotate the selected '%s' joint, and see how well the skin transfer did on '%s'."%(j2, tfPlaneB))

    return True

#------------

if not np or not KDTree or not str(sys.version).startswith("3"):
    utils.confirmDependencies()