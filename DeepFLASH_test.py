import torch
import sys
import argparse
from configs.getConfig import getConfig
from fileIO.io import saveConfig2Json
from fileIO.io import createExpFolder
from torch.utils.data import DataLoader
import SimpleITK as sitk
import os, glob
import numpy as np
from fileIO.io import safeLoadMedicalImg, convertTensorformat, loadData2


def loadDataVol(inputfilepath):
    SEG, COR, AXI = [0,1,2]
    targetDim = 2
    for idx, filename in enumerate (sorted(glob.glob(inputfilepath), key=os.path.getmtime)):
        img = sitk.GetArrayFromImage(sitk.ReadImage(filename))
        img = np.rollaxis(img, 0, 3)
        temp = convertTensorformat(img,
                                sourceFormat = 'single3DGrayscale', 
                                targetFormat = 'tensorflow', 
                                targetDim = targetDim, 
                                sourceSliceDim = AXI)      
        if idx == 0:        
            outvol = temp
        else:
            outvol  = np.concatenate((outvol , temp), axis=0)
    return outvol
    # outvol = input_src_data

def runExp(config, srcreal, tarreal, velxreal,velyreal, velzreal, srcimag, tarimag, velximag, velyimag, velzimag):
    #%% 1. Set configration and device    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


    #%% 2. Set Data
    import numpy as np
    from fileIO.io import safeLoadMedicalImg, convertTensorformat, loadData2

    # Load training data
    SEG, COR, AXI = [0,1,2]
    targetDim = 2
    import os, glob

    ##################LOAD REAL NET DATA##########################
    input_src_data_R = loadDataVol(srcreal)
    input_tar_data_R = loadDataVol(tarreal)
    input_vel_data_x = loadDataVol(velxreal)
    input_vel_data_y = loadDataVol(velyreal)
    input_vel_data_z = loadDataVol(velzreal)
    input_vel_data_R = np.concatenate((input_vel_data_x, input_vel_data_y,input_vel_data_z ), axis=3)

    input_src_data_I = loadDataVol(srcimag)
    input_tar_data_I = loadDataVol(tarimag)
    input_vel_data_x_I = loadDataVol(velximag)
    input_vel_data_y_I = loadDataVol(velyimag)
    input_vel_data_z_I = loadDataVol(velzimag)
    input_vel_data_I = np.concatenate((input_vel_data_x_I, input_vel_data_y_I,input_vel_data_y_I ), axis=3)
    from torchvision import transforms
    from fileIO.io import safeDivide

    xNorm = lambda img : safeDivide(img - np.min(img), (np.max(img) - np.min(img))) - 0.5
    trans3DTF2Torch = lambda img: np.moveaxis(img, -1, 0)
    img_transform = transforms.Compose([
        xNorm,
        trans3DTF2Torch
    #    transforms.ToTensor()
    ])
    from src.DataSet import DataSet2D, DataSetDeep, DataSetDeepPred
    training = DataSetDeep (source_data_R = input_src_data_R, target_data_R = input_tar_data_R,  groundtruth_R = input_vel_data_R, source_data_I = input_src_data_I, target_data_I = input_tar_data_I,  groundtruth_I = input_vel_data_I, transform=img_transform, device = device  )


    from src.DFModel import DFModel
    def weights_init_uniform(m):
        classname = m.__class__.__name__
        # for every Linear layer in a model..
        if classname.find('Linear') != -1:
            # apply a uniform distribution to the weights and a bias=0
            m.weight.data.uniform_(0.0, 1.0)
            m.bias.data.fill_(0)   
    deepflashnet = DFModel(net_config = config['net'], 
                        loss_config = config['loss'],
                        device=device)
    deepflashtestnet = DFModel(net_config = config['net'], 
                        loss_config = config['loss'],
                        device=device)
    #%% 6. Training and Validation
    loss = deepflashnet.trainDeepFlash(training_dataset=training, training_config = config['training'], valid_img= None, expPath = None)

if __name__ == "__main__":
    configName = 'deepflash'
    config = getConfig(configName)
    parser = argparse.ArgumentParser()
    parser.add_argument('--im_src_realpart', type=str, help="root directory of real parts of source images")
    parser.add_argument('--im_tar_realpart', type=str, help="root directory of real parts of target images")
    parser.add_argument('--im_vel_realX', type=str, help="root directory of real parts of velocity fields (X direction)")
    parser.add_argument('--im_vel_realY', type=str, help="root directory of real parts of velocity fields (Y direction)")
    parser.add_argument('--im_vel_realZ', type=str, help="root directory of real parts of velocity fields (Z direction)")

    parser.add_argument('--im_src_imaginarypart', type=str, help="root directory of imaginary parts of source images")
    parser.add_argument('--im_tar_imaginarypart', type=str, help="root directory of imaginary parts of target images")
    parser.add_argument('--im_vel_imagX', type=str, help="root directory of imaginary parts of source images (X direction)")
    parser.add_argument('--im_vel_imagY', type=str, help="root directory of imaginary parts of velocity fields (Y direction)")
    parser.add_argument('--im_vel_imagZ', type=str, help="root directory of imaginary parts of velocity fields (Z direction)")
    
    args = parser.parse_args()

    runExp(config, args.im_src_realpart, args.im_tar_realpart, args.im_vel_realX, args.im_vel_realY,args.im_vel_realZ, \
        args.im_src_imaginarypart, args.im_tar_imaginarypart, args.im_vel_imagX, args.im_vel_imagY,args.im_vel_imagZ)


