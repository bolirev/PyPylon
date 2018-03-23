"""
   Interface to basler cameras
"""
import pypylon


def camera2name(cam):
    """
    Convert camera names to a more user friendly name
    """
    camname = str(cam)
    camname = camname[camname.find('Basler'):camname.find(')')]
    camname = camname.replace(' ', '_').replace('(', '')
    return camname


def findcamera(camname):
    """Look for a camera with a given name.

    :param camname: A camera name e.g. Basler_acA2040-90umNIR_22325468
    :type camname: str
    """
    if not isinstance(camname, str):
        raise TypeError('Camera name should be a string')
    for cam in pypylon.factory.find_devices():
        cam = pypylon.factory.create_device(cam)
        if camname == camera2name(cam):
            return cam
    raise NameError('Camera {} not found'.format(camname))


def set_cam_properties(cam, properties):
    """ Assign cameras properties

    :param cam: camera to be updated
    :type cam: pypylon camera
    :param properties: the camera properties to be assigned
    :type properties: dict
    """
    if not isinstance(properties, dict):
        raise TypeError('Properties should be a dictionary')
    # Todo check cam type
    need2close = False
    if not cam.opened:
        need2close = True
        cam.open()
    for key, val in properties.items():
        try:
            cam.properties[key] = val
        except KeyError as e:
            print('Key not assignable {}'.format(key))
            raise e
    if need2close:
        cam.close()
