import sys
if len(sys.argv) <= 7 or len(sys.argv) >= 9:
    print('usage: <llm_temperature> <sentence_transformer_model> <which_textbook> <what_to_test> <num_to_generate> <threshold>')
    print('---Argument explanations---')
    print('\tllm: language model to use')
    print('\tllm_temperature: temperature to use with openai model')
    print('\tsentence_transformer_model: sentence transformer model to use for embeddings')
    print('\twhich textbook to use for evaluation, options: dsa_2214, dsa_6114, cs_3190')
    print('\twhat_to_test: what to test for evaluation from the following: concepts, outcomes, key_terms')
    print('\tnum_generated: number of generated concepts, outcomes, or key_terms to get')
    print('\tthreshold: threshold for evaluation metrics to pass')

    sys.exit()

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_path)

llm = sys.argv[1]
temp = float(sys.argv[2])
st_model = sys.argv[3]

textbook = sys.argv[4]
if textbook != 'dsa_6114' and textbook != 'cs_3190' and textbook != 'dsa_2214':
    print('invalid textbook arg. use dsa_2214, dsa_6114, or cs_3190')
    sys.exit()

if textbook == 'dsa_6114' or textbook == 'cs_3190':
    raise NotImplementedError('Textbooks currently do not have any associated data. Please use dsa_2214 in the meantime')

testing = sys.argv[5]
if testing != 'concepts' and testing != 'outcomes' and testing != 'outcomes':
    print('invalid what_to_test arg. use concepts, outcomes, or key_terms')
    sys.exit()

num_generated = int(sys.argv[6])
threshold = float(sys.argv[7])

from dotenv import load_dotenv
from os import environ, getenv
load_dotenv()
environ['OPENAI_API_KEY'] = getenv('OPENAI_API_KEY')

from src.generator import RAGKGGenerator
from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric, FaithfulnessMetric
from src.metrics import SemanticSimilarity, AnswerCorrectness
import pandas as pd
import os
from src.llms import OpenAIModel, HuggingFaceLLM

print('Loading environment variables...')
link = getenv(textbook) # Testing 2214 data structures textbook here
 
if textbook == 'dsa_2214':
    chapters = [
        'Data Structures and Algorithms',
        'Mathematical Preliminaries',
        'Algorithm Analysis',
        'Lists, Stacks, and Queues',
        'Binary Trees',
        'Non-Binary Trees',
        'Internal Sorting',
        'File Processing and External Sorting',
        'Searching',
        'Indexing',
        'Graphs',
        'Lists and Arrays Revisited',
        'Advanced Tree Structures',
        'Analysis Techniques',
        'Lower Bounds',
        'Patterns of Algorithms',
        'Limits to Computation',
    ]
elif textbook == 'dsa_6114':
    chapters = [
        'The Role of Algorithms in Computing',
        'Getting Started',
        'Growth of Algoritmhs',
        'Divide-and-Conquer',
        'Probabilistic Analysis and Randomized Algorithms',
        'Heapsort',
        'Quicksort',
        'Sorting in Linear Time',
        'Medians and Order Statistics',
        'Elementary Data Structures',
        'Hash Tables',
        'Binary Search Trees',
        'Red-Black Trees',
        'Augmenting Data Structures',
        'Dynamic Programming',
        'Greedy Algorithms',
        'Amortized Analysis',
        'B-Trees',
        'Fibonacci Heaps',
        'van Emde Boas Trees',
        'Data Structure for Disjoint Sets',
        'Elementary Graph Algoritmhs',
        'Minimum Spanning Trees',
        'Single-Source Shortest Paths',
        'All-Pairs Shortest Paths',
        'Maximum Flow',
        'Multithreaded Algoritmhs',
        'Matrix Operations',
        'Linear Programming',
        'Polynomials and the FFT',
        'Number-Theoretic Algorithms',
        'String Matching',
        'Computational Geometry',
        'NP-Completeness',
        'Approximation Algorithms'
    ]
elif textbook == 'cs_3190':
    chapters = [
        'Meet Hadoop',
        'MapReduce',
        'The Hadoop Distributed Filesystem',
        'YARN',
        'Hadoop I/O',
        'Developing a MapReduce Application',
        'How MapReduce Works',
        'MapReduce Types and Formats',
        'MapReduce Features',
        'Setting up a Hadoop Cluster',
        'Administering Hadoop',
        'Avro',
        'Parquet',
        'Flume',
        'Sqoop',
        'Pig',
        'Hive',
        'Crunch',
        'Spark',
        'HBase',
        'Zookeeper',
        'Composable Data at Cerner',
        'Biological Data Science: Saving Lives with Software.',
        'Cascading'
    ]

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

print('Loading data...')
data = pd.read_csv('data/dsa_clifford_a_shaffer_3_2_java.csv')

if testing == 'concepts':
    actual = data['concepts']
else:
    actual = data['outcomes']

print('Constructing extractor...')
extractor = RAGKGGenerator([chapters] if isinstance(chapters, str) else chapters, 
                            CHUNK_SIZE, 
                            CHUNK_OVERLAP, 
                            OpenAIModel(model_name = llm),
                            textbooks = link,
                            st_model = st_model,
                            )


print(f'Generating {testing} using extractor...')
if testing == 'concepts':
    generated, retrieved = extractor.identify_concepts(num_generated)
    actual = [c.split('::') for c in data['concepts']]
elif testing == 'outcomes':
    generated, retrieved = extractor.identify_outcomes(num_generated)
    actual = [o.split('::') for o in data['outcomes']]
else:
    generated, retrieved = extractor.identify_key_terms(num_generated)

metrics = [SemanticSimilarity(st_model = extractor.embedding_model), AnswerRelevancyMetric(model = extractor.llm), AnswerCorrectness(model = extractor.llm), FaithfulnessMetric(model = extractor.llm), ContextualPrecisionMetric(model = extractor.llm), ContextualRecallMetric(model = extractor.llm)]
results = extractor.evaluate(testing, num_generated, actual, metrics = metrics)

if not os.path.exists('./results'):
    os.mkdir('./results/')
    os.chdir('./results/')
else:
    os.chdir('./results/')

print('Writing results to file...')
with open(f'results_{textbook}_{testing}_{st_model}_{extractor.llm.get_model_name()}.txt', 'w') as f:
    f.write('-' * 20 + '\n')
    f.write(f'OPENAI MODEL: {extractor.llm.get_model_name()}\n')
    f.write(f'TEMPERATURE: {temp}\n')
    f.write(f'SENTENCE TRANSFORMER: {extractor.embedding_model}\n')
    f.write(f'TEXTBOOK: {textbook}\n')
    f.write(f'CHAPTERS TESTED: {extractor.chapters}\n')
    f.write(f'CHUNK SIZE: {CHUNK_SIZE}\n')
    f.write(f'CHUNK OVERLAP: {CHUNK_OVERLAP}\n')
    f.write('-' * 20 + '\n')

    averages = {}
    i = 0
    for r in results:
        query = r['input']
        output = r['output']
        name = r['name']
        score = r['score']
        reason = r['reason']
        expected = r['expected']

        f.write('-' * 20 + '\n')
        f.write(f'CHAPTER: {extractor.chapters[i]}\n')
        f.write(f'METRIC: {name} ---> SCORE: {score} ---> {"FAILURE" if score < threshold else "SUCCESS"}\n')
        f.write('\n')
        f.write(f'REASON: {reason}\n')
        f.write('\n')
        f.write(f'QUERY: {query}\n')
        f.write('\n')
        f.write(f'EXPECTED {testing.upper()}: {expected}')
        f.write('\n')
        f.write(f'GENERATED {testing.upper()}: {output}\n')  
        f.write('-' * 20 + '\n')

        if name not in averages:
            averages[name] = score
        else:
            averages[name] += score

        if i % len(metrics) == 0 and i != 0:
            i += 1 # we have 5 metrics so each chapter should get 5 writes

    for k in averages.keys():
        averages[k] /= len(extractor.chapters) # calculate average metric scores across all chapters

    f.write(f'')
    f.write('AVERAGE SCORES:\n')
    for k, v in averages.items():
        f.write(f'{k}: {v}\n')

print(f'Evaluation complete. Results written to results/results_{textbook}_{testing}_{st_model}_{extractor.llm.get_model_name()}.txt')
