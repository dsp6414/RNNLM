import os
import json
import logging
import argparse
import torch
from model.model import *
from model.loss import *
from model.metric import *
from data_loader import get_loader
from trainer import Trainer
from logger import Logger

logging.basicConfig(level=logging.INFO, format='')

def main(config, resume):
    train_logger = Logger()

    train_dataset, data_loader = get_loader(config, mode='train', vocab=None,
                                            seq_len=config['data_loader']['seq_len'],
                                            batch_size=config['data_loader']['batch_size'],
                                            min_word_count=config['data_loader']['min_word_count'])
    train_vocab = train_dataset.get_vocab()
    _, valid_data_loader = get_loader(config, mode='valid', vocab=train_vocab,
                                   seq_len=config['data_loader']['seq_len'],
                                   batch_size=config['data_loader']['batch_size'])
    config['model']['ntoken'] = len(train_vocab)
    print(config)
    model = eval(config['arch'])(config['model'])
    model.summary()

    loss = eval(config['loss'])
    metrics = [eval(metric) for metric in config['metrics']]

    trainer = Trainer(model, loss, metrics,
                      resume=resume,
                      config=config,
                      data_loader=data_loader,
                      valid_data_loader=valid_data_loader,
                      train_logger=train_logger)

    trainer.train()

if __name__ == '__main__':
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(description='PyTorch Template')
    parser.add_argument('-c', '--config', default=None, type=str,
                        help='config file path (default: None)')
    parser.add_argument('-r', '--resume', default=None, type=str,
                        help='path to latest checkpoint (default: None)')

    args = parser.parse_args()

    config = None
    if args.resume is not None:
        if args.config is not None:
            logger.warning('Warning: --config overridden by --resume')
        config = torch.load(args.resume)['config']
    elif args.config is not None:
        config = json.load(open(args.config))
        path = os.path.join(config['trainer']['save_dir'], config['name'])
        assert not os.path.exists(path), "Path {} already exists!".format(path)
    assert config is not None

    main(config, args.resume)