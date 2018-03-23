""" Record from n basler camera

camera config is specified by a yaml file
"""

import argparse
import ctypes
import time
import multiprocessing as mp
from multiprocessing import Queue, Process
import os
import yaml
import numpy as np
from setproctitle import setproctitle
import pypylon
from pybasler.logger import LZ4DiffLogger
from pybasler.basler import camera2name, set_cam_properties


def parser_recordcam():
    """ parser for the main function
    """
    parser = argparse.ArgumentParser()
    arghelp = 'Configuration file'
    parser.add_argument('--config',
                        type=str,
                        default='',
                        help=arghelp)
    arghelp = 'Process title'
    parser.add_argument('--proctitle',
                        type=str,
                        default='basler_pyrecorder',
                        help=arghelp)
    return parser


def configure_camera(config):
    """ configure and create camera
    """
    # Load configuration
    for camd in pypylon.factory.find_devices():
        if camera2name(camd) == config['name']:
            cam = pypylon.factory.create_device(camd)
            cam.open()
            params = dict()
            for key, item in config.items():
                if 'name' == key:
                    continue
                if 'folder' == key:
                    continue
                if 'nframe' == key:
                    continue
                if 'buffer_size' == key:
                    continue
                params[key] = item
            set_cam_properties(cam, params)
            return cam, config['folder']
    raise NameError('CameraNotFound')


def record(config):
    """ record one camera with config as properties
    """
    # Get certain userfull variable
    if 'name' in config.keys():
        camname = config['name']
    else:
        raise KeyError('config should contain a name')

    if 'nframe' in config.keys():
        nframe = config['nframe']
    else:
        raise KeyError('config should contain a nframe')

    if 'buffer_size' in config.keys():
        n_buffer = config['buffer_size']
    else:
        raise KeyError('config should contain a buffer_size')

    if 'logger_threshold' in config.keys():
        logth = config['logger_threshold']
    else:
        raise KeyError('config should contain a logger_threshold')

    # Load configuration
    cam, folder = configure_camera(config)

    # Create shared array
    # of size n_buffer*image-size
    # this array is not locked so the ready_queue should
    # have the same size as the n_buffer
    array_dim = (cam.properties['Height'],
                 cam.properties['Width'])
    nimel = np.prod(array_dim)
    m = mp.Array(ctypes.c_ubyte, int(n_buffer*nimel))
    array = np.frombuffer(m.get_obj(), dtype=np.uint8)

    # Create the control queue to avoid reading/writing on array
    ready_queue = Queue(maxsize=n_buffer)

    # Create a file name from camera name
    filename = os.path.join(folder, camera2name(cam) + '.lz4')

    # Create a logger to store the data
    logger = LZ4DiffLogger(m, ready_queue, nimel)
    logger.filename = filename
    logger.threshold = logth
    logger.start()

    # Start recording
    print('Start recording')
    t_start = time.time()
    try:
        for rot_i in cam.grab_inrings(nframe, array, n_buffer):
            ready_queue.put_nowait(rot_i)
        ready_queue.put(None)
    except RuntimeError as e:
        print('ERROR: ', camname)
        ready_queue.put(None)
        raise (e)

    logger.join()
    cam.close()
    t_end = time.time()
    t_span = t_end - t_start
    print('End recording at {} fps'.format(nframe/t_span))
    return 'Done'


if __name__ == '__main__':
    """
       Recording from ncameras
    """
    args = parser_recordcam().parse_args()
    setproctitle(args['proctitle'])
    configfile = args['config']

    with open(configfile) as fp:
        config = yaml.load(fp)

    # Check if shared parameters
    if 'camera-all' in config.keys():
        shared_conf = config['camera-all']
    else:
        shared_conf = dict

    # Create a list of cameras
    cameras_key = list()
    for key in config.keys():
        cami = key.split('-')
        if len(cami) != 2:
            continue
        if cami[1].isdigit():
            cameras_key.append(key)

    # Number of camera found
    n_cameras = len(cameras_key)

    # Create a config dict for each camera
    cam_config = list()
    for key in cameras_key:
        cconf = config[key]
        for k, v in shared_conf.items():
            cconf[k] = v
        cam_config.append(cconf)

    # Start a list of processes
    # one for each camera, not that logger will spawn
    # a child process
    processes = list()
    for i in range(n_cameras):
        processes.append(Process(target=record,
                                 args=(cam_config[i],)))
    for p in processes:
        p.start()
    for p in processes:
        p.join()
