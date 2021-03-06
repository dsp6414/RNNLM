import nltk
import json
import os
import torch
import torch.utils.data as data
from collections import defaultdict, Counter
import argparse

class Vocabulary(object):
    def __init__(self):
        self.w2i = defaultdict(lambda: len(self.w2i))
        self.UNK = self.w2i["<unk>"]
        self.EOS = self.w2i["<eos>"]
        self.i2w = defaultdict()

    def add_word(self, word):
        return self.w2i[word]

    def build_vocab(self):
        self.w2i = defaultdict(lambda: self.UNK, self.w2i)
        self.i2w = {v: k for k, v in self.w2i.items()}

    def __len__(self):
        return len(self.i2w)

class Dataset(data.Dataset):
    def __init__(self, path, vocab=None, seq_len=20, batch_size=32, min_word_count=5):
        self.vocab = Vocabulary() if vocab is None else vocab
        self.min_word_count = min_word_count
        if vocab is None:
            self._data_unk(path)
            self.vocab.build_vocab()
        self.data = self._get_data(path)
        self.batch_size = batch_size
        self.nbatch = len(self.data) // (batch_size * seq_len)
        self.seq_len = seq_len
        #self.data = self.data[:self.nbatch * self.batch_size * self.seq_len + 1]
        self.src_seqs = list(self._get_src_seqs())[:self.nbatch * self.batch_size]
        self.tgt_seqs = list(self._get_tgt_seqs())[:self.nbatch * self.batch_size]
        self.data = None
        #print('batch_size: ' + str(self.batch_size))
        #print('nbatch: ' + str(self.nbatch))
        #print('seq_len: ' + str(self.seq_len))
        #print('nsrc: ' + str(len(self.src_seqs)))
        #print('ntgt: ' + str(len(self.tgt_seqs)))
        self.num_total_seqs = len(self.src_seqs)

    def _data_unk(self, path):
        counter = Counter()
        with open(path, 'r') as f:
            ids = []
            for line in f:
                tokens = line.strip().split(" ")
                counter.update(tokens)
        words = [word for word, count in counter.items() if count >= self.min_word_count]
        for word in words:
            self.vocab.add_word(word)

    def _get_data(self, path):
        with open(path, 'r') as f:
            ids = []
            for line in f:
                ids.extend([self.vocab.add_word(x) for x in
                       line.strip().split(" ") + [self.vocab.EOS]])

        return ids

    def _get_src_seqs(self):
        for i in range(0, len(self.data) - 1, self.seq_len):
            yield self.data[i:i + self.seq_len]

    def _get_tgt_seqs(self):
        for i in range(1, len(self.data), self.seq_len):
            yield self.data[i:i + self.seq_len]

    def build_vocab(self):
        self.vocab.build_vocab()

    def get_vocab(self):
        return self.vocab

    def __getitem__(self, index):
        src_seq = self.src_seqs[index]
        tgt_seq = self.tgt_seqs[index]
        src_seq = torch.LongTensor(src_seq)
        tgt_seq = torch.LongTensor(tgt_seq)
        return src_seq, tgt_seq

    def __len__(self):
        return self.num_total_seqs

def collate_fn(data):
    def merge(sequences):
        lengths = [len(seq) for seq in sequences]
        padded_seqs = torch.zeros(len(sequences), max(lengths)).long()
        for i, seq in enumerate(sequences):
            end = lengths[i]
            padded_seqs[i, :end] = seq[:end]
        return padded_seqs, lengths

    # We don't need it for LM
    #data.sort(key=lambda x:len(x[0]), reverse=True)

    src_seqs, tgt_seqs = zip(*data)

    src_seqs, src_lengths = merge(src_seqs)
    tgt_seqs, tgt_lengths = merge(tgt_seqs)

    #return src_seqs, src_lengths, tgt_seqs, tgt_lengths
    return src_seqs, tgt_seqs

def get_loader(config, mode='train', vocab=None, shuffle=False,
               seq_len=20, batch_size=32, min_word_count=5):
    path = config['data_loader']['data_dir'] + '/' + mode + '.txt'
    dataset = Dataset(path, vocab, seq_len, batch_size, min_word_count)
    data_loader = torch.utils.data.DataLoader(dataset=dataset,
                                              batch_size=batch_size,
                                              shuffle=shuffle,
                                              collate_fn=collate_fn)

    return dataset, data_loader