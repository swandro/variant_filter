#Annotate the varscan file

import Bio.SeqIO
from collections import defaultdict
import math
import argparse

    

#####DEFAULTS#########
# minimum_coverage = 10
# distance_from_gap = 300
# min_variant_freq = 0.7
#######################

########Parse the arguments###########
parser = argparse.ArgumentParser(description='Filter out bad variants. Takes in varscan snp calls. Outputs 2 files, one of bad variants and one of good variants.')
parser.add_argument('-in', metavar='variant_file', dest = "variant_file", type=str, nargs='?',
                   help='Table of variants generated by varscan.')
parser.add_argument('-gb', metavar='genbank_file',  dest = "genbank_file", type=str, nargs='?',
                   help='Genbank file of genome used to call variants.')
parser.add_argument('-c', dest = 'minimum_coverage', metavar='minimum_coverage', type=int, nargs='?', default = 10,
                   help='Minimum total coverage at base to call a mutation. Default = 10')
parser.add_argument('-d', dest = 'distance_from_gap', metavar='distance_from_gap', type=int, nargs='?', default = 300,
                   help='Minimum distance of variant from ends of contig or from assembly gap. Default = 300')
parser.add_argument('-f',dest =  "min_variant_freq", metavar='min_variant_freq', type=int, nargs='?', default = 0.7,
                   help='Minimum frequency of variant. Default = 0.7')
parser.add_argument('-out', dest = "output_file", metavar='output_file', type=str, nargs='?', default = '',
                   help='Prefix for output file')
args = parser.parse_args()
########################################
#if not path(args.varaint_file).isfile():
#   raise SystemExit("asdlfkjadlshfaokg")

with open("test_files/V587.gb",'r') as openfile:
    for record in Bio.SeqIO.parse(openfile, "genbank"):
        #Each entry is a Bio.SeqRecord.SeqRecord, the key is the name of the contig
        genome[record.name] = record

for feature in genome['KB946439'].features:
    pass

#####################Import files###################################
# Import the genome as a dictionary called "genome". 
# Each entry is a contig
genome = dict()
with open(args.genbank_file,'r') as openfile:
    for record in Bio.SeqIO.parse(openfile, "genbank"):
        #Each entry is a Bio.SeqRecord.SeqRecord, the key is the name of the contig
        genome[record.name] = record

#Import the varscan file as a list called "variant_list".
# Every item is list made from a line from the variant file
variant_list = []
column_headers = ''
with open(args.variant_file,'r') as openfile:
    column_headers = openfile.readline().strip().split()
    for line in openfile:
        variant_list.append(line.strip().split())

############################################################################


#########################Helper functions#############################
#Function to add range of bases to ignore
def add_bases_to_ignore(range_set, position, direction):
    '''
    Updates the input set "range_set" to include new values based on "position" and "direction"
    Returns nothing
    range_set = set of numbers. Current set of bases to ignore.
    position = number. Start of new range of bases to ignore
    direction = "+" or "-". Direction of ignore range starting at position. +:right, -:left
    '''
    #direction = ignore bases before (-) or after (+). Length is DISTANCE_FROM_GAP global variable
    assert(type(range_set) == set), "first argument must be a set"
    assert(type(position) == int), "position must be an integer"
    assert(direction in ["+","-"]), "direction must be either + or -"
    if direction == "+":
        range_set.update(set(range(position, args.distance_from_gap)))
    elif direction == "-":
        range_set.update(set(range(position - args.distance_from_gap, position+1)))

def get_annotation(contig, position):
    '''
    Return the feature that is located at "position" of "contig". Uses the "genome" dictionary.
    If no annotation, returns ''.
    '''
    for feature in genome[contig].features:
        if feature.type in ["CDS","tRNA","rRNA"] and feature.__contains__(int(position)):
            return feature
    return ''

def get_aa_change(contig, feature, position, new_base):
    '''
    Returns the original and new amino acid as a tuple for a given mutation. (old_aa, new_aa)
    contig = String. name of contig
    feature = Feature. feture where mutation is located. Output from get_annotation().
    position = number. Position of mutation
    new_base = String. New nucleotide.
    '''
    #Get original nt and aa
    original_aas = feature.qualifiers["translation"][0]
    original_nt = str(feature.extract(genome[contig]).seq)
    #Get mutated nt and aa
    contig_with_mutation = list(genome[contig].seq)
    contig_with_mutation[position-1] = new_base
    contig_with_mutation = ''.join(contig_with_mutation)
    new_nt = feature.extract(contig_with_mutation)
    new_aas = str(Bio.Seq.Seq(new_nt).translate(table=11))[:-1]
    #make start codon M (wrongly translated as I )
    if new_aas[0] != "M":
        new_aas = "M" + new_aas[1:]
    #get original and new amino acid
    position_in_gene = position - int( feature.location.start)
    original_aa = original_aas[math.ceil(position_in_gene/3)]
    new_aa = new_aas[math.ceil(position_in_gene/3)]
    #Return tuple of (original aa, new aa)
    return((original_aa, new_aa))

############################################################################

#Get ranges for ends of contigs and assembly gaps


        

#Make dictionary with contig names as keys and list of ranges to ignore as values
bad_ranges = dict()
for contig in genome.keys():
    #Start with begining and end of contig
    bad_ranges[contig] = set()
    add_bases_to_ignore(bad_ranges[contig], 1, "+")
    contig_size = len(genome['KB946415']._seq)
    add_bases_to_ignore(bad_ranges[contig], contig_size, "-")
    #Add any assembly gaps
    for feature in genome[contig].features:
        if feature.type == "assembly_gap":
            start_position = int(feature.location.start)
            end_position = int(feature.location.end)
            add_bases_to_ignore(bad_ranges[contig], start_position, "-")
            add_bases_to_ignore(bad_ranges[contig], end_position, "+")

#Go though each variant and decide if they pass the filters or not
bad_variants = []
almost_good_variants = []
good_variants = []
bad_variant_reasons = defaultdict(int)
mutated_feature = []

for variant in variant_list:
    #Filter out variants if reference sequence is N
    if variant[2] == "N":
        variant.append("reference_N")
        bad_variants.append(variant)
        bad_variant_reasons["reference_N"] += 1
        continue
    #Filter out if not in a gene
    position = int(variant[1])
    new_nt = variant[3]
    contig = variant[0]
    feature = get_annotation(contig, position)
    if not feature:
        variant += [str(('','')),"intergenic"]
        bad_variants.append(variant)
        bad_variant_reasons["intergenic"] += 1
        continue
    #Get amino acid change
    aa_change = get_aa_change(contig, feature, position, new_nt)
    #Get sysnonymous vs nonsynonymous
    synonymous = aa_change[0] == aa_change[1]
    #Filter out synonymous
    if synonymous:
        variant.append("synonymous " + str(aa_change))
        bad_variants.append(variant)
        bad_variant_reasons["synonymous"] += 1
        continue
    #Filter out variants near assembly gaps or ends of contigs
    if int(variant[1]) in bad_ranges[variant[0]]:
        variant.append("near_gap")
        bad_variants.append(variant)
        bad_variant_reasons["near_gap"] += 1
        continue
    #Filter out variants with low coeverage
    if int(variant[5]) < args.minimum_coverage:
        variant.append("low_coverage")
        bad_variants.append(variant)
        bad_variant_reasons["low_coverage"] += 1
        continue
    #Filter out variants with low variant frequency
    if float(variant[6][:-1]) < args.min_variant_freq:
        variant.append("low_frequency")
        bad_variants.append(variant)
        bad_variant_reasons["low_frequency"] += 1
        continue
    #Filter out multiple mutations in the same gene
    feature_id = feature.qualifiers.locus_tag
        for gene in mutated_feature:
            if gene == feature_id:
                bad_variants.append(variant)
                bad_variant_reasons["multiple_mutations_in_same_gene"] += 1
                continue
    #Add amino acid change
    variant.extend([aa_change[0], aa_change[1]])
    almost_good_variants.append(variant)
    #Add gene to list of mutated genes
    mutated_feature.append(feature_id)
#Problems: getting aa change to bad variants
   #Filtering out first mutation when there are multiple
    
#############Write output files################
#write good variants
if good_variants:
    with open(args.output_file + "_good_snps.tsv",'w') as openfile:
        openfile.write('\t'.join(column_headers + ["old_aa","new_aa"]) + '\n')
        for variant in good_variants:
            openfile.write('\t'.join(variant) + '\n')

##write bad variants
#Use input name + _bad_snps.tsv if no output name given
if not args.output_file:
    args.output_file = args.variant_file.split('.')[0]
  
if bad_variants:
    with open(args.output_file + "_bad_snps.tsv",'w') as openfile:
        openfile.write('\t'.join(column_headers + ["filter_reason"]) + '\n')
        for variant in bad_variants:
            openfile.write('\t'.join(variant) + '\n')

print()
print("Variant_filter has finished running")
print("Good variants = {}".format(str(len(good_variants))))
print("Bad variants = {}".format(str(len(bad_variants))))
print("Reasons variants were rejected:")
for reason in bad_variant_reasons.keys():
    print('\t' + "{} : {}".format(bad_variant_reasons[reason], reason))
###############################################

#####REMAINING TO DO
#multiple smps per gene
#output alignments