from setproctitle import setproctitle
from recordcamsv3 import record
from multiprocessing import Process
import yaml

if __name__ == '__main__':
    configfile = 'config.yaml'

    with open(configfile) as fp:
        config = yaml.load(fp)

    if 'camera-all' in config.keys():
        shared_conf=config['camera-all']
    else:
        shared_conf=dict
    shared_conf['nframe']=500000
    shared_conf['buffer_size']=1000

    cameras_key = list()
    for key in config.keys():
        cami = key.split('-')
        if len(cami)!=2:
            continue
        if cami[1].isdigit():
            cameras_key.append(key)

    n_cameras = len(cameras_key)

    cam_config = list()
    for key in cameras_key:
        cconf = config[key]
        for k,v in shared_conf.items():
            cconf[k]=v
        cam_config.append(cconf)
    
    processes=list()
    for i in range(n_cameras):
        processes.append(Process(target=record, args=(cam_config[i],)))
    for p in processes:
        p.start()
    for p in processes:
        p.join()
