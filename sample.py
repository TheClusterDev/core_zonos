# Input data
in_dotenv_needed_models = {
    "Zyphra/Zonos-v0.1-transformer",
    "Zyphra/Zonos-v0.1-hybrid",
}

in_dotenv_needed_paths = {
    "HF_HOME": "./models/hf_download",
}

de_disable_torch_compile_default=True
import sys
if sys.platform == "linux":
    de_disable_torch_compile_default=False
if sys.platform == "darwin":
    de_disable_torch_compile_default=False


in_dotenv_needed_params = {
    "DISABLE_TORCH_COMPILE_DEFAULT": de_disable_torch_compile_default,
    "DEBUG_MODE": False,

}

#LCX1.0##################################################################
#FILELOADER##############################################################
#########################################################################
debug_mode=False
LCX_APP_NAME="CROSSOS_FILE_CHECK"
DEFAULT_MODEL_CONFIG_FILE = "configmodel.txt"
in_model_config_file=DEFAULT_MODEL_CONFIG_FILE
# --- Helper Functions ---
#dotenv prefixes
PREFIX_MODEL="PATH_MODEL_"
PREFIX_PATH="PATH_NEEDED_"
LOG_PREFIX="CROSSOS_LOG"
import re
import os 
from pathlib import Path
from typing import Dict, Set, Any, Union
def model_to_varname(model_path: str, prefix: str) -> str:
    """Converts a model path to a dotenv-compatible variable name"""
    model_name = model_path.split("/")[-1]
    varname = re.sub(r"[^a-zA-Z0-9]", "_", model_name.upper())
    return f"{prefix}{varname}"

def varname_to_model(varname: str, prefix: str) -> str:
    """Converts a variable name back to original model path format"""
    if varname.startswith("PATH_MODEL_"):
        model_part = varname[prefix.len():].lower().replace("_", "-")
        return f"Zyphra/{model_part}"
    return ""

def read_existing_config(file_path: str) -> Dict[str, str]:
    """Reads existing config file and returns key-value pairs"""
    existing = {}
    path = Path(file_path)
    if path.exists():
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        existing[parts[0].strip()] = parts[1].strip()
    return existing

def update_model_paths_file(
    models: Set[str],
    paths: Dict[str, str],
    params: Dict[str, Any],
    file_path: str 
) -> None:
    """Updates config file, adding only new variables"""
    existing = read_existing_config(file_path)
    new_lines = []
    
    # Process models
    for model in models:
        varname = model_to_varname(model, PREFIX_MODEL)
        if varname not in existing:
            print(f"{LOG_PREFIX}: Adding Model rquirement to config: {model}")
            new_lines.append(f"{varname} = ./models/{model.split('/')[-1]}")
    
    # Process paths - now handles any path keys
    for key, value in paths.items():
        varname = model_to_varname(key, PREFIX_PATH)
        if varname not in existing:
            print(f"{LOG_PREFIX}: Adding path rquirement to config: {key}")
            new_lines.append(f"{varname} = {value}")
    
    # Process params
    for key, value in params.items():
        if key not in existing:
            print(f"{LOG_PREFIX}: Adding Parameter rquirement to config: {key}")
            new_lines.append(f"{key} = {value}")
    
    # Append new lines if any
    if new_lines:
        with open(file_path, 'a') as f:
            f.write("\n" + "\n".join(new_lines) + "\n")

def parse_model_paths_file(file_path: str , dotenv_needed_models, dotenv_needed_paths ) -> tuple[
    Set[str], Dict[str, str], Dict[str, Union[bool, int, float, str]]
]:
    """Reads config file and returns loaded variables"""
    loaded_models = {}
    loaded_paths = {}
    loaded_params = {}
    loaded_models_values= {}
    existing = read_existing_config(file_path)
    
    for key, value in existing.items():
        # Handle model paths
        if key.startswith(PREFIX_MODEL):
            for mod in dotenv_needed_models:
                #we find out if the current key value belongs to one of our models
                if key == model_to_varname(mod,PREFIX_MODEL):
                    #if a path has been defined and it exists we use the local path
                    if value and os.path.isdir(value):
                        loaded_models[mod] = value
                    else:
                        #else we use the model id so its downloaded from github later
                        loaded_models[mod] = mod
                    #still we collect the values to show to the user so he knows what to fix in config file
                    loaded_models_values[mod] = value
        # Handle ALL paths (not just HF_HOME)
        elif key.startswith(PREFIX_PATH):
            for mod in dotenv_needed_paths:
                if key == model_to_varname(mod,PREFIX_PATH):
                    loaded_paths[mod] = value
        # Handle params with type conversion
        else:
            if value.lower() in {"true", "false"}:
                loaded_params[key] = value.lower() == "true"
            elif value.isdigit():
                loaded_params[key] = int(value)
            else:
                try:
                    loaded_params[key] = float(value)
                except ValueError:
                    loaded_params[key] = value
    
    return loaded_models, loaded_paths, loaded_params, loaded_models_values

def is_online_model(model: str,dotenv_needed_models, debug_mode: bool = False) -> bool:
    """Checks if a model is in the online models set."""
    is_onlinemodel = model in dotenv_needed_models
    if debug_mode:
        print(f"Model '{model}' is online: {is_onlinemodel}")
    return is_onlinemodel

import os
def count_existing_paths(paths):
    """
    Checks if each path in the list exists.
    Returns:
        - summary (str): Summary of found/missing count
        - all_found (bool): True if all paths were found
        - none_found (bool): True if no paths were found
        - details (list of str): List with "[found]" or "[not found]" per path
    """
    total = len(paths)
    if total == 0:
        return "No paths provided.", False, True, []
    found_count = 0
    details = []
    for path in paths:
        if os.path.exists(path):
            found_count += 1
            details.append(f"[!FOUND!]: {path}")
        else:
            details.append(f"[MISSING]: {path}")
    missing_count = total - found_count
    all_found = (missing_count == 0)
    none_found = (found_count == 0)
    summary = f"Found {found_count}, missing {missing_count}, out of {total} paths."
    return summary, all_found, none_found, details


def remove_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)]
    return text


def get_hf_model_cache_dirname(model_id: str) -> str:
    """
    Returns the HF cache directory name for a given model.
    """
    base = "models--"
    return base + model_id.replace('/', '--')


def lcx_checkmodels(dotenv_needed_models,dotenv_loaded_paths, dotenv_loaded_models, dotenv_loaded_models_values  ):
    #TODO: load dynamically from array
    test_models_hf = []
    test_models_dir=[]
    test_paths_dir=[]
    
    #add model paths as path and as hf cache path
    for currmodel in dotenv_needed_models:
        test_models_hf.append(f"{dotenv_loaded_paths["HF_HOME"]}{os.sep}hub{os.sep}{get_hf_model_cache_dirname(currmodel)}{os.sep}snapshots")
        test_models_dir.append(f"{dotenv_loaded_models[  currmodel]}")
    
    #add needed dirs as path
    for curr_path in dotenv_loaded_paths:
        test_paths_dir.append(f"{dotenv_loaded_paths[  curr_path]}")
    
    if debug_mode:
        print(f"test pathf hf: {test_models_hf}")
        print(f"test pathf dirs: {test_models_dir}")
        
    print(f"{LCX_APP_NAME}: checking model accessibility")
    summary_hf, all_exist_hf, none_exist_hf, path_details_hf = count_existing_paths(test_models_hf)

    print(f"\n-Searching Group1: Model HF_HOME----------------------------------------------")
    for line in path_details_hf:
        print_line= remove_suffix(line, "snapshots")
        print(print_line)

    summary_dir, all_exist_dir, none_exist_dir, path_details_dir = count_existing_paths(test_models_dir)
    print("-Searching Group2: Manual Model Directories-----------------------------------")
    for line in path_details_dir:
        print_line= remove_suffix(line, "model_index.json")
        print_line= remove_suffix(print_line, "config.json")
        print(print_line)

    summary_path, all_exist_path, none_exist_path, path_details_path = count_existing_paths(test_paths_dir)
    print("-Searching Group3: Needed Directories-----------------------------------------")
    for line in path_details_path:
        print(line)


    print("")
    #we show the dir values to the user
    if all_exist_dir==False:
        print("-Values in config (resolved to your OS)---------------------------------------")
        for key in dotenv_loaded_models_values:
            print(f"{key}: {os.path.abspath(dotenv_loaded_models_values[key])}")
    if all_exist_path==False:
        for key in dotenv_loaded_paths:
            print(f"{key}: {os.path.abspath(dotenv_loaded_paths[  key])}")

    print("")
    
    #Needed Dirs summary
    if all_exist_path == False:
        print("-Needed Paths---------------------------------------------------") 
        print("Not all paths were found. Check documentation if you need them")

    print("-Needed Models--------------------------------------------------")
    #some model directories were missing 
    if none_exist_dir == False and all_exist_dir == False: 
        print ("Some manually downloaded models were found. Some might need to be downloaded!")
    #some hf cache models were missing
    if  all_exist_hf == False and none_exist_hf==False:
        print ("Some HF_Download models were found. Some might need to be downloaded!")
    if none_exist_dir and none_exist_hf:
        print ("No models were found! Models will be downloaded at next app start")

    if all_exist_hf==True or all_exist_dir==True:
        print("RESULT: It seems all models were found. Nothing will be downloaded!") 
    sys.exit()

# Update the config file
update_model_paths_file(in_dotenv_needed_models, in_dotenv_needed_paths, in_dotenv_needed_params, in_model_config_file)

# Read back the values
out_dotenv_loaded_models, out_dotenv_loaded_paths, out_dotenv_loaded_params , out_dotenv_loaded_models_values= parse_model_paths_file(in_model_config_file, in_dotenv_needed_models,in_dotenv_needed_paths)

if debug_mode:
    print("Loaded models:", out_dotenv_loaded_models)
    print("Loaded models values:", out_dotenv_loaded_models_values)
    print("Loaded paths:", out_dotenv_loaded_paths)
    print("Loaded params:", out_dotenv_loaded_params)
    
    
os.environ['HF_HOME'] = out_dotenv_loaded_paths["HF_HOME"]
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
#os.environ["TOKENIZERS_PARALLELISM"] = "true"


#originalblock#################################
import argparse
import sys
parser = argparse.ArgumentParser()
parser.add_argument('--share', action='store_true')
parser.add_argument("--server", type=str, default='0.0.0.0')
parser.add_argument("--port", type=int, required=False)
parser.add_argument("--inbrowser", action='store_true')
parser.add_argument("--output_dir", type=str, default='./outputs')
parser.add_argument("--checkmodels", action='store_true')
args = parser.parse_args()
###################################
# for win desktop probably use --server 127.0.0.1 --inbrowser
# For linux server probably use --server 127.0.0.1 or do not use any cmd flags

#return out_dotenv_loaded_models, out_dotenv_loaded_paths, out_dotenv_loaded_params 

if args.checkmodels: 
    lcx_checkmodels(in_dotenv_needed_models,out_dotenv_loaded_paths, out_dotenv_loaded_models, out_dotenv_loaded_models_values )


if debug_mode:
    print("---current model paths---------")
    for id in out_dotenv_loaded_models:
        print (f"{id}: {out_dotenv_loaded_models[id]}")

####################################################################################################################
####################################################################################################################
####################################################################################################################
#prefix end#########################################################################################################























disable_torch_compile_default=out_dotenv_loaded_params["DISABLE_TORCH_COMPILE_DEFAULT"]


AI_MODEL_DIR_TF=out_dotenv_loaded_models[   "Zyphra/Zonos-v0.1-transformer"]
AI_MODEL_DIR_HY=out_dotenv_loaded_models[    "Zyphra/Zonos-v0.1-hybrid"]


AI_MODEL_DIR= AI_MODEL_DIR_TF





import torch
import torchaudio
from zonos.model import Zonos
from zonos.conditioning import make_cond_dict
from zonos.utils import DEFAULT_DEVICE as device




config_path=f"{AI_MODEL_DIR}{os.sep}config.json"
model_path=f"{AI_MODEL_DIR}{os.sep}model.safetensors"


model = Zonos.from_local(config_path, model_path, device=device)

wav, sampling_rate = torchaudio.load("assets/exampleaudio.mp3")
speaker = model.make_speaker_embedding(wav, sampling_rate)

torch.manual_seed(421)

cond_dict = make_cond_dict(text="Hello, world! this is core Zonos!", speaker=speaker, language="en-us")
conditioning = model.prepare_conditioning(cond_dict)

codes = model.generate(conditioning,  disable_torch_compile=disable_torch_compile_default)

wavs = model.autoencoder.decode(codes).cpu()
torchaudio.save("sample.wav", wavs[0], model.autoencoder.sampling_rate)
