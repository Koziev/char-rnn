# -*- coding: utf-8 -*- 

# вариант с TimeDistributedDense

import os
import numpy
import sys
import random
import copy

from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, TimeDistributedDense
from keras.layers.recurrent import SimpleRNN
from keras.layers.recurrent import LSTM
from keras.optimizers import SGD

chars_path =  os.path.expanduser('~/Corpus/Chars/ru/chars.txt');

print 'Reading char sequences from ', chars_path

max_lines = 100000000 # использовать столько строк (предложений) из входного корпуса для накопления статистики

chars_set = set() # список встретившихся символов без повтора
id2char = {} # для получения символа по его индексу


# токены начала и конца цепочки добавляем руками, так как в явном виде их в корпусе нет
chars_set.add( '\r' ) # <s> начало
chars_set.add( '\n' ) # </s> конец

with open( chars_path, 'r' ) as f:
    for num,line in enumerate(f):
        chars_set.update( list(line.strip().decode("utf-8")) )
        if num==max_lines:
            break

nchar = len(chars_set)
print 'Number of unique chars=', len(chars_set)

for i,c in enumerate(chars_set):
    id2char[i] = c

# для отладки: в файл выведем словарь символов
with open( 'id2char.txt', 'w' ) as ff:
    for (id,ch) in id2char.iteritems():
        if ch=='\r':
            ff.write( str(id) + u' ==> <s>\n' );
        elif ch=='\n':
            ff.write( str(id) + u' ==> </s>\n' );
        else:
            ff.write( (str(id) + u' ==> ' + ch + u'\n').encode('utf-8') );
        
        
# преобразование символа во входной вектор 0|1's
# TODO: использовать слой Embedding
char2vector = {}
for i,c in enumerate(chars_set):
    v = numpy.zeros(nchar)
    v[i] = 1
    char2vector[c] = v


input_size = nchar
features_size = 100
output_size = nchar
batch_len = 128
N_SAMPLE_PER_EPOCH = 10000000
NUMBER_OF_EPOCH = 10 # кол-во повторов тренировки по одному набору данных


model = Sequential()

rnn_layer = LSTM( input_dim=input_size, output_dim=features_size, activation='tanh', return_sequences=True )

model.add(rnn_layer)

model.add(TimeDistributedDense(output_dim=output_size))
model.add(Activation('softmax'))
#sgd = SGD(lr=0.05, decay=1e-6, momentum=0.9, nesterov=True)

print 'Compiling the model...'
#model.compile(loss='categorical_crossentropy', optimizer=sgd)
model.compile(loss='categorical_crossentropy', optimizer='rmsprop')

print( 'Start training...' )

total_session_count = 0
total_sample_count = 0

# накапливаем последовательности разной длины в отдельных списках
len2list_of_seq = {}

# количество накопленных в len2list_of_seq последовательностей
sample_count = 0

# здесь получим макс. длину последовательности символов, которую мы запомнили
max_seq_len=0

# в этот файл будем записывать генерируемые моделью строки
output_samples_path = 'samples.txt'
if os.path.isfile(output_samples_path):
    os.remove(output_samples_path)


# идем по файлу с предложениями
with open( chars_path, 'r' ) as f:
    for line in f:
        charseq = line.strip().decode("utf-8")
        xlen = len(charseq)
        if xlen>1:
            if xlen in len2list_of_seq:
                len2list_of_seq[xlen].append( charseq )
            else:
                len2list_of_seq[xlen] = [ charseq ]
            sample_count = sample_count+1
            max_seq_len = max( max_seq_len, xlen )

        if sample_count>N_SAMPLE_PER_EPOCH:

            #for seq_len, n_sequence in sorted( [ (seqlen, len(sequences)) for seqlen, sequences in len2list_of_seq.iteritems() ], key=lambda z : -z[1] ):
            #    print 'seq_len=', seq_len, 'n_sequence=', n_sequence
           
            print 'Training...'
            
            isession = 0
            
            # группируем последовательности одной длины в сессию
            # сортируем последовательности так, чтобы последней обрабатывалась группа с самым большим числом сэмплов
            
            for seqlen, n_sequence in sorted( [ (seqlen, len(sequences)) for seqlen, sequences in len2list_of_seq.iteritems() ], key=lambda z : z[1] ):

                if n_sequence>100:

                    print 'seqlen=', seqlen, 'n_sequence=', n_sequence

                    xlen = seqlen + 2 -1 # +2 токена <s> и </s> и один токен убираем, чтобы работало предсказание для последнего символа предложения 
                    
                    # из общего числа отберем треть для проверки
                    n_test = int(n_sequence*0.3)
                    
                    # остальное - тренировка
                    n_train = n_sequence-n_test
                    
                    # тензоры для входных последовательностей и выходных эталонных данных
                    X_train = numpy.zeros( (n_train,xlen,input_size) )
                    Y_train = numpy.zeros( (n_train,xlen,input_size) )

                    X_test = numpy.zeros( (n_test,xlen,input_size) )
                    Y_test = numpy.zeros( (n_test,xlen,input_size) )

                    # заполняем тензоры
                    itrain=0;
                    itest=0
                    for isample,rawseq in enumerate(len2list_of_seq[seqlen]):
                        #print 'rawseq=', rawseq
                        #sys.exit()
                        seq = '\r' + rawseq + '\n'
                        
                        is_training = True
                        if itrain>=n_train:
                             is_training = False
                             
                        for itime in range(0,len(seq)-1):
                            x = seq[itime]
                            y = seq[itime+1]
                            
                            #print 'itime=', itime, 'x=', x, 'y=', y

                            if is_training:
                                X_train[itrain,itime,:] = char2vector[ x ]
                                Y_train[itrain,itime,:] = char2vector[ y ]
                            else:
                                X_test[itest,itime,:] = char2vector[ x ]
                                Y_test[itest,itime,:] = char2vector[ y ]
                        
                        if is_training:        
                            itrain = itrain+1
                        else:    
                            itest = itest+1

                    print 'n_sequence=', n_sequence, 'itrain=', itrain, 'itest=', itest
                    acc = model.fit( X_train, Y_train, batch_size=batch_len, nb_epoch=NUMBER_OF_EPOCH, validation_data=[X_test,Y_test] )
                    #print 'acc=', acc.history.get('loss')
                    #sys.exit()
                    
                    isession = isession+1
                    
                    
                    with open( output_samples_path, 'a' ) as fsamples:
                    
                        fsamples.write( '\n\n\nAfter session ' + str(isession) + ' seqlen=' + str(seqlen) + ' n_sequence=' + str(n_sequence) + ':\n\n' )

                        for igener in range(0,10):
                            # сделаем сэмплинг цепочки символов
                            # начинаем всегда с символа <s>
                            last_char = u'\r'
                            model.reset_states();
                        
                            # буфер для накопления сгенерированной строки
                            sample_str = u''
                            sample_seq = last_char
                    
                            while len(sample_str)<300:

                                xlen = len(sample_seq)
                                X_gener = numpy.zeros( (1,xlen,input_size) )
                        
                                for itime,uch in enumerate( list( sample_seq ) ):
                                    X_gener[0,itime,:] = char2vector[ uch ]
                    
                                # получаем результат - цепочка предсказаний, из которой нам нужен только
                                # последний вектор
                                Y_gener = model.predict( X_gener, batch_size=1, verbose=0 )[0,:]
                        
                                #print 'DEBUG Y_gener.shape=', Y_gener.shape
                                #sys.exit()
                        
                                yv = Y_gener[xlen-1,:]
                            
                                sum_y = numpy.sum(yv) # должно быть ~1, так как softmax
                            
                                ch_p = sorted( [(ichar,p/sum_y) for ichar,p in enumerate(yv)], key = lambda z : -z[1] )
                                #print 'ch_p[', chcount, ']=', ch_p
                            
                                # выбираем новый символ
                                p = random.random()
                                sum_p = 0
                                selected_char = ' '
                                for (ich,pch) in ch_p:
                                    sum_p = sum_p + pch
                                    if sum_p >= p:
                                        selected_char = id2char[ich]
                                        break
                            
                                if selected_char==u'\n':
                                    break
                        
                                sample_str = sample_str + selected_char
                                sample_seq = sample_seq + selected_char
                                last_char = selected_char
                            
                            print 'sample_str=', sample_str
                            fsamples.write( sample_str.encode('utf-8') + '\n' )
                    
        
            sys.exit()

