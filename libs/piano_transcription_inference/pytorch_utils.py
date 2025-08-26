import torch
import time
import numpy as np
from tqdm import tqdm


def move_data_to_device(x, device):
    if 'float' in str(x.dtype):
        x = torch.Tensor(x)
    elif 'int' in str(x.dtype):
        x = torch.LongTensor(x)
    else:
        return x

    return x.to(device)


def append_to_dict(dict, key, value):
    if key in dict.keys():
        dict[key].append(value)
    else:
        dict[key] = [value]
 

def forward_origin(model, x, batch_size):
    """Forward data to model in mini-batch. 
    
    Args: 
      model: object
      x: (N, segment_samples)
      batch_size: int

    Returns:
      output_dict: dict, e.g. {
        'frame_output': (segments_num, frames_num, classes_num),
        'onset_output': (segments_num, frames_num, classes_num),
        ...}
    """
    
    output_dict = {}
    device = next(model.parameters()).device
    
    pointer = 0
    total_segments = int(np.ceil(len(x) / batch_size))
    
    while True:
        print('Segment {} / {}'.format(pointer, total_segments))
        if pointer >= len(x):
            break

        batch_waveform = move_data_to_device(x[pointer : pointer + batch_size], device)
        pointer += batch_size

        with torch.no_grad():
            model.eval()
            batch_output_dict = model(batch_waveform)

        for key in batch_output_dict.keys():
            append_to_dict(output_dict, key, batch_output_dict[key].data.cpu().numpy())

    for key in output_dict.keys():
        output_dict[key] = np.concatenate(output_dict[key], axis=0)

    return output_dict


def forward_old(model, x, batch_size, progress_callback=None):
    output_dict = {}
    device = next(model.parameters()).device
    param_dtype = next(model.parameters()).dtype  # 获取模型dtype

    pointer = 0
    total_segments = int(np.ceil(len(x) / batch_size))

    with torch.no_grad():
        model.eval()
        with tqdm(total=total_segments, desc="Processing", unit="seg") as pbar:
            while pointer < len(x):
                # 转换为 Tensor 并匹配 dtype
                batch_waveform = torch.tensor(x[pointer: pointer + batch_size], dtype=param_dtype).to(device)

                pointer += batch_size
                batch_output_dict = model(batch_waveform)

                for key in batch_output_dict.keys():
                    if key not in output_dict:
                        output_dict[key] = []
                    output_dict[key].append(batch_output_dict[key].cpu().numpy())

                pbar.update(1)
                if progress_callback:
                    elapsed = pbar.format_dict['elapsed']
                    rate = pbar.format_dict['rate'] if pbar.format_dict['rate'] else 0
                    progress_callback(pointer, total_segments, elapsed, rate)

    for key in output_dict.keys():
        output_dict[key] = np.concatenate(output_dict[key], axis=0)

    return output_dict


def forward(model, x, batch_size, progress_callback=None):
    output_dict = {}
    device = next(model.parameters()).device
    param_dtype = next(model.parameters()).dtype

    pointer = 0
    total_segments = int(np.ceil(len(x) / batch_size))

    start_time = time.time()
    processed_segments = 0

    with torch.no_grad():
        model.eval()
        with tqdm(total=total_segments, desc="Processing", unit="seg", disable=True) as pbar:
            while pointer < len(x):
                # 转换为 Tensor 并匹配 dtype
                batch_waveform = torch.tensor(x[pointer: pointer + batch_size], dtype=param_dtype).to(device)

                pointer += batch_size
                batch_output_dict = model(batch_waveform)

                for key in batch_output_dict.keys():
                    if key not in output_dict:
                        output_dict[key] = []
                    output_dict[key].append(batch_output_dict[key].cpu().numpy())

                pbar.update(1)
                processed_segments += 1

                if progress_callback:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    rate = processed_segments / elapsed if elapsed > 0 else 0
                    progress_callback(pointer, total_segments, elapsed, rate)

    for key in output_dict.keys():
        output_dict[key] = np.concatenate(output_dict[key], axis=0)

    return output_dict
