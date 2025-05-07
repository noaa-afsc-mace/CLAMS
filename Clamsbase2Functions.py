
from math import *
from numpy import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import traceback,  sys


class Clamsbase2Functions(object):

    def __init__(self, db, ship, survey,  progressDlg=None):
        self.ship=ship
        self.survey=survey
        self.db=db
        self.progress=progressDlg
        self.oldway_mix=False

        #  make sure we have the bioschema attribute
        self.db.bioSchema = self.db.label
        if not hasattr(self.db, 'bioSchema'):
            self.db.bioSchema = 'clamsbase2'


    def computeCatchSummary(self,  haul,  partition,  species_code,  subcategory):
        try:
            self.catchSum=[]
            # clear
            # additional sample_data params
            #catch_summary_params=['sample_id','WeightInHaul','SampledWeight','NumberInHaul','SampledNumber','FrequencyExpansion','InMix','WholeHauled']
            #catch_summary_types=['integer','float','float','integer','integer','float','integer','integer']
            #sample_order=['WholeHaul',  'SortingTable',  'Mix']
            # figure out the split business
            split_exp = 1.

            #  check to make sure this is a catch retaining event (we skip open codend events)
            query2 = self.db.dbQuery("SELECT parameter_value FROM "+self.db.bioSchema+".event_data WHERE ship="+self.ship+
                    " AND survey=" + self.survey + " AND event_id="+haul + " AND partition = '" + partition +
                    "' AND event_parameter='PartitionWeight'")
            parameter_value, = query2.first()

            #  initialize default whole haul ID (assume sample is not whole hauled)
            wholehaul_id = None

            #  if we have a value this is a catch retaining event
            if parameter_value is not None:

                query2 = self.db.dbQuery("SELECT sample_id, parent_sample FROM "+self.db.bioSchema+".samples WHERE ship=" +
                        self.ship+ " AND survey="+self.survey+" AND event_id="+haul+" AND species_code=100001 AND partition='"+
                        partition+"'")
                table_id = query2.first()[0]

                # grab the weight type
                # ADDED by Robert to determine if loadcell was used instead of checking for TBD since weight should now be written in for non-splitters
                sortquery = self.db.dbQuery("SELECT parameter_value FROM "+self.db.bioSchema+".event_data WHERE ship="+self.ship+
                        " AND survey="+self.survey+" AND event_id="+haul+ " AND partition = '"+partition+
                        "' AND event_parameter='PartitionWeightType'")
                weighttype = sortquery.first()[0]

                 # if the weight type is load cell...
                if weighttype.lower() != 'not_subsampled':
                    # get total sample table weight
                    query3 = self.db.dbQuery("SELECT sample_id FROM "+self.db.bioSchema+".samples WHERE ship="+self.ship+
                            " AND survey="+self.survey+" AND event_id="+haul+ " AND partition = '"+partition+
                            "' AND species_code=100000")
                    wholehaul_id = query3.first()[0]

                    query3 = self.db.dbQuery("SELECT sum(baskets.weight) FROM "+self.db.bioSchema+".samples, "+
                            self.db.bioSchema+".baskets WHERE "+self.db.bioSchema+".samples.sample_id="+
                            self.db.bioSchema+".baskets.sample_id "+ "AND "+self.db.bioSchema+".samples.survey="+
                            self.db.bioSchema+".baskets.survey AND "+self.db.bioSchema+".samples.ship="+self.db.bioSchema+
                            ".baskets.ship AND samples.ship="+self.ship+" AND samples.survey="+self.survey+
                            " AND samples.event_id="+haul+ " AND samples.partition = '"+partition+
                            "' AND samples.parent_sample="+table_id)
                    t, =query3.first()
                    table_wt=float(t)
                    if table_wt==0.:
                        print('something stinks here...')
                        return (False, [])# if there are no basket weights for this haul/partition, game is over
                    else:
                        #have to subtract the wholehauled species
                        query3 = self.db.dbQuery("SELECT sum(baskets.weight) FROM "+self.db.bioSchema+".samples, "+self.db.bioSchema+".baskets WHERE samples.sample_id=baskets.sample_id "+
                        "AND samples.survey=baskets.survey AND samples.ship=baskets.ship AND samples.ship="+self.ship+" AND samples.survey="+self.survey+
                        " AND samples.event_id="+haul+ " AND samples.partition = '"+partition+"' AND samples.parent_sample="+wholehaul_id)
                        wholehaul_sample_wt=query3.first()[0]
                        if wholehaul_sample_wt==None:
                            wholehaul_sample_wt=0.
                        else:
                            wholehaul_sample_wt=float(wholehaul_sample_wt)
                        split_exp=(float(parameter_value)-float(wholehaul_sample_wt))/table_wt

            # figure out mix split

            query2 = self.db.dbQuery("SELECT sample_id, parent_sample FROM "+self.db.bioSchema+".samples WHERE ship="+self.ship+" AND survey="+
            self.survey+" AND event_id="+haul+" AND species_code=100002 AND partition='"+partition+"'")# the traditional mix
            mix1_id,  parent_id =  query2.first()
            if mix1_id is not None:
                if self.oldway_mix:
                    query5 = self.db.dbQuery("SELECT sum(a.weight) FROM "+self.db.bioSchema+".baskets a, "+self.db.bioSchema+".samples b WHERE "+
                    "a.ship=b.ship AND a.survey=b.survey AND a.event_id=b.event_id AND a.sample_id=b.sample_id AND "+
                    "a.ship="+self.ship+" AND a.survey="+self.survey+
                    " AND a.event_id="+haul+" AND b.parent_sample="+mix1_id)
                    mixsubwt=float(query5.first()[0])
                    query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND sample_id="+mix1_id)
                    mixtotwt=float(query5.first()[0])
                    if mixsubwt>0:
                        mix1_exp=mixtotwt/mixsubwt
                    else:
                        mix1_exp=1.
                else:
                    query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND basket_type='Measure' AND sample_id="+mix1_id)
                    try:
                        mixsubwt=float(query5.first()[0])
                    except:
                        query5 = self.db.dbQuery("SELECT sample_id FROM "+self.db.bioSchema+".samples WHERE ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND parent_sample="+mix1_id)
                        baby_samples=''
                        for sample,  in query5:
                            baby_samples=baby_samples+sample+","
                        baby_samples=baby_samples[:-1]
                        # hmmm we have a mix but no mix subweight.  lets get a sum of species within the mix
                        query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND sample_id in("+baby_samples+")")
                        #print('stop')
                        mixsubwt=float(query5.first()[0])
                    query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND sample_id="+mix1_id)

                    # query5.first() can be None - what does that mean?

                    mixtotwt = float(query5.first()[0])
                    if mixsubwt>0:
                        mix1_exp=mixtotwt/mixsubwt
                    else:
                        mix1_exp=1.
            # repeat for mix2 - don't need th e"old way"
            query2 = self.db.dbQuery("SELECT sample_id, parent_sample FROM "+self.db.bioSchema+".samples WHERE ship="+self.ship+" AND survey="+
            self.survey+" AND event_id="+haul+" AND species_code=100004 AND partition='"+partition+"'")# the traditional mix
            mix2_id,  parent_id =  query2.first()
            if mix2_id is not None:
                query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+haul+" AND basket_type='Measure' AND sample_id="+mix2_id)
                mixsubwt=float(query5.first()[0])
                query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+haul+" AND sample_id="+mix2_id)
                mixtotwt=float(query5.first()[0])
                if mixsubwt>0:
                    mix2_exp=mixtotwt/mixsubwt
                else:
                    mix2_exp=1.
            # and now the submix
            query2 = self.db.dbQuery("SELECT sample_id, parent_sample FROM "+self.db.bioSchema+".samples WHERE ship="+self.ship+" AND survey="+
            self.survey+" AND event_id="+haul+" AND species_code=100003 AND partition='"+partition+"'")# the traditional mix
            submix1_id,  parent_id =  query2.first()# parent should be mix1

            if submix1_id is not None:
                if not parent_id == mix1_id:
                    print("this is baloney!")
                query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+haul+" AND basket_type='Measure' AND sample_id="+submix1_id)
                mixsubwt=float(query5.first()[0])
                query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+haul+" AND sample_id="+submix1_id)
                mixtotwt=float(query5.first()[0])
                if mixsubwt>0:
                    submix1_exp=mixtotwt/mixsubwt
                else:
                    submix1_exp=1.
                # now the kicker - submix gets scaled by mi1 as well sor a super mix expansion
                submix1_exp=submix1_exp

            # run throught the "species" samples
            if subcategory=='All':
                query2 = self.db.dbQuery("SELECT sample_id, parent_sample, sample_type, species_code, subcategory FROM "+self.db.bioSchema+".samples WHERE ship="+
                self.ship+" AND survey="+self.survey+" AND event_id="+haul+" AND sample_type='Species' AND partition='"+partition+"' AND species_code ="+species_code)
            else:
                query2 = self.db.dbQuery("SELECT sample_id, parent_sample, sample_type, species_code, subcategory FROM "+self.db.bioSchema+".samples WHERE ship="+
                self.ship+" AND survey="+self.survey+" AND event_id="+haul+" AND sample_type='Species' AND partition='"+partition+"' AND species_code ="+species_code+" AND subcategory='"+subcategory+"'")
            for sample_id, parent_sample, sample_type, spc_code, subcat  in  query2:
                vals=[]
                # compute catch summary data
                if partition[:-1] =='CamTrawl':# this is a camtrawl partition - there will be no sample "weight"
                    query5 = self.db.dbQuery("SELECT count(*) FROM "+self.db.bioSchema+".specimen WHERE ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND sampling_method='random' AND sample_id="+sample_id)
                    specimen_cnt, =query5.first()
                    val=[sample_id,                     # sample id
                                 spc_code,                  # species code
                                 subcat,                        # subcategory
                                 int(sample_id),                # sample id
                                 0.0,      # Weight In Haul
                                 0.0,              # Sampled Weight
                                 int(specimen_cnt),# Number In Haul
                                 int(specimen_cnt),                   # Sampled Number
                                 1.0,    #
                                 0,                         #
                                 0]                     #
                    self.catchSum.append(val)
                    return (True, self.catchSum)
                    #[sample id, species code, subcategory, sample id
                else:# physical catch paritions
                    # subsample expansions
                    query5 = self.db.dbQuery("SELECT sum(weight), sum(count) FROM "+self.db.bioSchema+".baskets WHERE basket_type='Count' AND  ship="+
                    self.ship+" AND survey="+self.survey+" AND event_id="+haul+" AND sample_id="+sample_id)
                    count_subwt, count_subcnt = query5.first()
                    if not count_subwt in [None, '', 0]:
                        count_subwt=float(count_subwt)
                        count_subcnt=float(count_subcnt)
                    query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE basket_type='Measure' AND  ship="+
                    self.ship+" AND survey="+self.survey+" AND event_id="+haul+" AND sample_id="+sample_id)
                    measure_subwt,  = query5.first()
                    if not measure_subwt in [None, '', 0]:
                        measure_subwt=float(measure_subwt)
                    query5 = self.db.dbQuery("SELECT count(*) FROM "+self.db.bioSchema+".specimen WHERE ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND sampling_method='random' AND sample_id="+sample_id)
                    measure_subcnt, =query5.first()
                    # Slight adjustment here, due to change in forwardOnly dbConnection change..
                    # Seems like if you perform operation *.first() from a query twice, it blows up now.
                    if not measure_subcnt in [None, '', 0]:
                        measure_subcnt=float(measure_subcnt)
                    query5 = self.db.dbQuery("SELECT sum(weight) FROM "+self.db.bioSchema+".baskets WHERE  ship="+self.ship+" AND survey="+self.survey+
                    " AND event_id="+haul+" AND sample_id="+sample_id)
                    totwt, =query5.first()
                    if totwt:
                        totwt =float(totwt)
                    else:
                        totwt = 0
                    if count_subwt in [None, '', 0]:# no count basket
                        if measure_subwt in [None, '', 0]:# no measure bakset
                            # no count or measure baskets
                            subcnt=0
                            subwt=0
                        else:# yes measure basket
                            subcnt=measure_subcnt
                            subwt=measure_subwt
                            cnt_ratio=0
                    else:# yes count basket
                        if measure_subwt in [None, '', 0]:# no measure bakset
                            # only count basket
                            subcnt=count_subcnt
                            subwt=count_subwt
                        else:# yes measure basket and count basket
                        #  combine the measured count + the number counted
                            subcnt=measure_subcnt+count_subcnt
                            subwt=measure_subwt+count_subwt

                    if not measure_subcnt in [None, '', 0]:
                        #  count ratio is the total number of fish that have been sampled / number that have been measured
                        cnt_ratio=subcnt/measure_subcnt
                    else:# nothing was measured
                        cnt_ratio=0
                    if not totwt>0:# this is a "stub" sample
                        return (False, [])
                    if subwt>0:
                        sub_exp=(totwt/subwt)
                    else:
                        sub_exp=1.
                    if parent_sample==mix1_id:# this sample is in the mix1
                        tot_exp=sub_exp*split_exp*mix1_exp
                        inmix=1
                        whhaul=0
                    elif parent_sample==mix2_id:# this sample is in the mix2
                        tot_exp=sub_exp*split_exp*mix2_exp
                        inmix=2
                        whhaul=0
                    elif parent_sample==submix1_id:# this sample is in the submix1 - child of mix1
                        tot_exp=sub_exp*split_exp*submix1_exp*mix1_exp
                        inmix=3
                        whhaul=0
                    elif parent_sample==wholehaul_id:# this sample has been wholehauled
                        tot_exp=sub_exp
                        inmix=0
                        whhaul=1
                    else:
                        tot_exp=sub_exp*split_exp# non mix splitter expansions
                        inmix=0
                        whhaul=0

                    #  the total measured expansion is the total expansion * count ratio
                    tot_measure_exp=tot_exp*cnt_ratio

                    if subwt==0 and totwt>0:# this is where nothing was subsampled and everything was tossed
                        subwt=totwt
                    vals.append([sample_id,                     # sample id
                                 spc_code,                  # species code
                                 subcat,                        # subcategory
                                 int(sample_id),                # sample id
                                 round(subwt*tot_exp, 10),      # Weight In Haul
                                 round(subwt, 10),              # Sampled Weight
                                 int(round(subcnt*tot_exp, 0 )),# Number In Haul
                                 int(subcnt),                   # Sampled Number
                                 round(tot_measure_exp, 10),    #
                                 inmix,                         # which mix category is it in (1 is mix 1, 2 is mix 2, 3 is submix1
                                 whhaul])                       #
                    #[sample id, species code, subcategory, sample id, WeightInHaul,SampledWeight,NumberInHaul,SampledNumer,FrequencyExpansion,InMix,WholeHauled]
                #populate variable
                if len(vals)>1:# this is where the animal is inside and outside of the mix - should be rare and only in old "migrated" data
                    wt_in_haul=[]
                    sampled_wt=[]
                    num_in_haul=[]
                    sampled_num=[]
                    in_mix=[]
                    wh_haul=[]
                    for val in vals:
                        wt_in_haul.append(val[4])
                        sampled_wt.append(val[5])
                        num_in_haul.append(val[6])
                        sampled_num.append(val[7])
                        in_mix.append(val[9])
                        wh_haul.append(val[10])

                    if 0 in sampled_num:# some part of this multi sample has not numeric count - this should be xuper rare!!!
                        ind=sampled_num.index(0)
                        n=array(num_in_haul)
                        w=array(wt_in_haul)
                        p=sum(n/w)# num per kg
                        num_in_haul[ind]=p*wt_in_haul[ind]

                    self.catchSum.append([val[0], val[1], val[2], val[3], sum(wt_in_haul), sum(sampled_wt), round(sum(num_in_haul), 0), sum(sampled_num), sum(num_in_haul)/sum(sampled_num),  sum(in_mix)/2., sum(wh_haul)/2.])
    #                    return (True, self.catchSum)
                elif len(vals)==1:
                    self.catchSum.append(vals[0])

    #                    return (True, self.catchSum)
                else:
                    return (False, [])
            # The case when 'All' is passed as an argument into this function- return a sum of all entries
            if len(self.catchSum)>1:
                newSumKG=0
                newSumN=0
                for CS in self.catchSum:
                    newSumKG=CS[4]+newSumKG
                    newSumN=CS[6]+newSumN
                self.newCatchSum=[['NA',self.catchSum[0][1], 'All', -99, newSumKG, newSumKG, newSumN, newSumN, 1, 0, 1]]
                return (True,  self.newCatchSum)
            else:
                return (True, self.catchSum)
        except:
            return (False, traceback.format_exception(*sys.exc_info()))
            print(traceback.format_exception(*sys.exc_info()))


    def getLengthFrequency(self, haul,  partition,  species_code,  subcategory, non_random=False, return_N=False):
        lengthFreq=[]
        N=0
        for i in range(100):
            lengthFreq.append(0)
        try:
            if subcategory=='All': # combine all the subcategories
                query = self.db.dbQuery("SELECT subcategory FROM "+self.db.bioSchema+".samples WHERE ship="+self.ship+" AND survey="+self.survey+
                 " AND event_id="+haul+" AND species_code="+species_code+" AND partition= '"+partition+"'")
                subs=[]
                for sub,  in query:
                    subs.append(sub)

            else:
                subs=[subcategory]

            for sub in subs:
                status, comp=self.computeCatchSummary(haul, partition, species_code, sub)
                if not status:
                    return(False, comp)
                exp_factor=comp[0][8]

                if non_random:
                    query = self.db.dbQuery(" SELECT a.length, c.subcategory "+
                                            " FROM "+self.db.bioSchema+".v_fish_lengths a "+
                                            " INNER JOIN "+self.db.bioSchema+".specimen b ON "+
                                            "(a.survey=b.survey AND a.ship=b.ship AND a.event_id=b.event_id "+
                                            " AND a.specimen_id = b.specimen_id) "+
                                            " INNER JOIN "+self.db.bioSchema+".samples c ON "+
                                            " (a.survey=c.survey and a.ship=c.ship and a.event_id=c.event_id and a.sample_id=c.sample_id) "+
                                            " WHERE a.survey="+self.survey+" AND a.ship="+self.ship+" AND a.event_id="+haul+
                                            " AND a.species_code="+species_code+" AND a.partition='"+partition+"'")
                else:
                    query = self.db.dbQuery(" SELECT a.length, c.subcategory "+
                                            " FROM "+self.db.bioSchema+".v_fish_lengths a "+
                                            " INNER JOIN "+self.db.bioSchema+".specimen b ON "+
                                            "(a.survey=b.survey AND a.ship=b.ship AND a.event_id=b.event_id "+
                                            " AND a.specimen_id = b.specimen_id and b.sampling_method='random') "+
                                            " INNER JOIN "+self.db.bioSchema+".samples c ON "+
                                            " (a.survey=c.survey and a.ship=c.ship and a.event_id=c.event_id and a.sample_id=c.sample_id) "+
                                            " WHERE a.survey="+self.survey+" AND a.ship="+self.ship+" AND a.event_id="+haul+
                                            " AND a.species_code="+species_code+" AND a.partition='"+partition+"'")
                for l, subcat in query:
                    if subcat in sub:
                        length=int(round(float(l), 0))
                        N+=1
                        if length==0:
                            length=1
                        if length>100:# this is a hack  to keep things from blowing up with fish larger than 100 cm e.g. all larger fish het assigned to 100 cm
                            length=100
                        lengthFreq[length-1]+=1.*exp_factor
            if return_N:
                return (True, lengthFreq, N)
            else:
                return (True, lengthFreq)
        except:
            return (False, traceback.format_exception(*sys.exc_info()))
            print(traceback.format_exception(*sys.exc_info()))

    def getLengthFrequencyBySex(self, haul,  partition,  species_code,  subcategory, non_random=False, return_N=False):
        lengthFreq=[]
        lengthFreqSex={}
        N=0
        try:
            if subcategory=='All': # combine all the subcategories
                query = self.db.dbQuery("SELECT subcategory FROM "+self.db.bioSchema+".samples WHERE ship="+self.ship+" AND survey="+self.survey+
                 " AND event_id="+haul+" AND species_code="+species_code+" AND partition= '"+partition+"'")
                subs=[]
                for sub,  in query:
                    subs.append(sub)
            else:
                subs=[subcategory]
            sexes=['Male','Female','Unsexed']
            for sex in sexes:# make empty holder
                lengthFreq=[]
                for i in range(100):
                    lengthFreq.append(0)
                lengthFreqSex.update({sex:lengthFreq})

            for sub in subs:
                status, comp=self.computeCatchSummary(haul, partition,  species_code, sub)
                #if partition =='Codend':
                if not status or len(comp)==0:
                    return (False, ['Bad catch data!'])
                exp_factor=comp[0][8]
                # queries were changed 11-2017 (NEL) to accomodate removal of generic 'lengths' from database and query new
                # v_fish_lengths view for specific length types
                if non_random:
                    query = self.db.dbQuery(" SELECT a.length, b.measurement_value, c.subcategory "+
                                            " FROM "+self.db.bioSchema+".v_fish_lengths a "+
                                            " LEFT JOIN "+self.db.bioSchema+".measurements b ON "+
                                            "(a.survey=b.survey AND a.ship=b.ship AND a.event_id=b.event_id "+
                                            " AND b.measurement_type='sex' AND a.specimen_id = b.specimen_id) "+
                                            " INNER JOIN "+self.db.bioSchema+".samples c ON "+
                                            " (a.survey=c.survey and a.ship=c.ship and a.event_id=c.event_id and a.sample_id=c.sample_id) "+
                                            " INNER JOIN "+self.db.bioSchema+".specimen d ON "+
                                            " (a.survey=d.survey and a.ship=d.ship and a.event_id=d.event_id and a.specimen_id=d.specimen_id) "+
                                            " WHERE a.survey="+self.survey+" AND a.ship="+self.ship+" AND a.event_id="+haul+
                                            " AND a.species_code="+species_code+" AND a.partition='"+partition+"'")
                else:
                    query = self.db.dbQuery(" SELECT a.length, b.measurement_value, c.subcategory "+
                                            " FROM "+self.db.bioSchema+".v_fish_lengths a "+
                                            " LEFT JOIN "+self.db.bioSchema+".measurements b ON "+
                                            "(a.survey=b.survey AND a.ship=b.ship AND a.event_id=b.event_id "+
                                            " AND b.measurement_type='sex' AND a.specimen_id = b.specimen_id) "+
                                            " INNER JOIN "+self.db.bioSchema+".samples c ON "+
                                            " (a.survey=c.survey and a.ship=c.ship and a.event_id=c.event_id and a.sample_id=c.sample_id) "+
                                            " INNER JOIN "+self.db.bioSchema+".specimen d ON "+
                                            " (a.survey=d.survey and a.ship=d.ship and a.event_id=d.event_id and a.specimen_id=d.specimen_id and d.sampling_method='random') "+
                                            " WHERE a.survey="+self.survey+" AND a.ship="+self.ship+" AND a.event_id="+haul+
                                            " AND a.species_code="+species_code+" AND a.partition='"+partition+"'")

                for l, s, subcat in query:
                    if subcat in sub:
                        length=int(round(float(l), 0))
                        N+=1
                        if length==0:
                            length=1
                        if length>100:# this is a hack  to keep things from blowing up with fish larger than 100 cm e.g. all larger fish het assigned to 100 cm
                            length=100

                        if s in ['Male', 'Female']:
                            lengthFreqSex[s][length-1]+=1.*exp_factor
                        else:
                            lengthFreqSex['Unsexed'][length-1]+=1.*exp_factor

            if return_N:
                return (True, lengthFreqSex, N)
            else:
                return (True, lengthFreqSex)
        except:
            return (False, traceback.format_exception(*sys.exc_info()))
            print(traceback.format_exception(*sys.exc_info()))


    def getRawLengthsBySex(self, haul, partition, species_code, subcategory):

        try:
            #  check if we're combining subcategories
            if (subcategory.lower() == 'all'):
                #  yes, we're combining them
                query = self.db.dbQuery("SELECT subcategory FROM " + self.db.bioSchema +
                        ".samples WHERE ship=" + self.ship + " AND survey=" + self.survey +
                        " AND event_id="+haul+" AND species_code="+species_code+" AND partition= '" +
                        partition+"'")
                subs = []
                for sub, in query:
                    subs.append(sub)
            else:
                #  no - operate on the specified subcategory only
                subs = [subcategory]

            length_vec=[]
            weight_vec=[]
            sex_vec=[]
            type_vec=[]

            # get primary and secondary length_type
            query1 = self.db.dbQuery("SELECT parameter_value FROM " + self.db.bioSchema +
                    ".species_data WHERE species_parameter='Primary_Length_Type' AND species_code=" +
                    species_code)
            primary_length_type, = query1.first()

            query1 = self.db.dbQuery("SELECT parameter_value FROM " + self.db.bioSchema +
                    ".species_data WHERE species_parameter='Secondary_Length_Type' AND species_code=" +
                    species_code)
            secondary_length_type, = query1.first()

            #  work through the subcategories
            for sub in subs:
                status, comp = self.computeCatchSummary(haul, partition, species_code, sub)
                if partition =='Codend':
                    if not status or len(comp)==0:
                        return (False, 'Bad catch data!', '','', '')
                exp_factor=comp[0][8]

                #  new method using updated v_fish_lengths
                query = self.db.dbQuery("SELECT length, length_type, sex FROM " + self.db.bioSchema +
                        ".V_FISH_LENGTHS WHERE ship=" + self.ship + " AND " +
                        "survey=" + self.survey + " AND event_id=" + haul + " AND " +
                        "species_code=" + species_code + " AND partition='" + partition +
                        "' AND subcategory='" + sub + "' AND sampling_method='random'")
                for length, length_type, sex in query:
                    length_vec.append(float(length))
                    type_vec.append(length_type)
                    weight_vec.append(exp_factor)
                    sex_vec.append(sex)

            return (True, length_vec,  sex_vec,  weight_vec,  type_vec)

        except:
            return (False, traceback.format_exception(*sys.exc_info()), '', '', '')
            print(traceback.format_exception(*sys.exc_info()))

    def getRawLengthsWithID(self, haul, partition, species_code, subcategory):

        try:
            #  check if we're combining subcategories
            if (subcategory.lower() == 'all'):
                #  yes, we're combining them
                query = self.db.dbQuery("SELECT subcategory FROM " + self.db.bioSchema +
                        ".samples WHERE ship=" + self.ship + " AND survey=" + self.survey +
                        " AND event_id="+haul+" AND species_code="+species_code+" AND partition= '" +
                        partition+"'")
                subs = []
                for sub, in query:
                    subs.append(sub)
            else:
                #  no - operate on the specified subcategory only
                subs = [subcategory]

            length_vec=[]
            weight_vec=[]
            ID_vec=[]
            type_vec=[]

            # get primary and secondary length_type
            query1 = self.db.dbQuery("SELECT parameter_value FROM " + self.db.bioSchema +
                    ".species_data WHERE species_parameter='Primary_Length_Type' AND species_code=" +
                    species_code)
            primary_length_type, = query1.first()

            query1 = self.db.dbQuery("SELECT parameter_value FROM " + self.db.bioSchema +
                    ".species_data WHERE species_parameter='Secondary_Length_Type' AND species_code=" +
                    species_code)
            secondary_length_type, = query1.first()

            #  work through the subcategories
            for sub in subs:
                status, comp = self.computeCatchSummary(haul, partition, species_code, sub)
                if partition =='Codend':
                    if not status or len(comp)==0:
                        return (False, 'Bad catch data!', '','', '')
                exp_factor=comp[0][8]

                #  new method using updated v_fish_lengths
                query = self.db.dbQuery("SELECT length, length_type, specimen_id, FROM " + self.db.bioSchema +
                        ".V_FISH_LENGTHS WHERE ship=" + self.ship + " AND " +
                        "survey=" + self.survey + " AND event_id=" + haul + " AND " +
                        "species_code=" + species_code + " AND partition='" + partition +
                        "' AND subcategory='" + sub + "' AND sampling_method='random'")
                for length, length_type, ID in query:
                    length_vec.append(float(length))
                    type_vec.append(length_type)
                    weight_vec.append(exp_factor)
                    ID_vec.append(ID)

            return (True, length_vec,  ID_vec,  weight_vec,  type_vec)

        except:
            return (False, traceback.format_exception(*sys.exc_info()), '', '', '')
            print(traceback.format_exception(*sys.exc_info()))


    def makeLFbySexFromLengths(self, length_vec,  weight_vec,  sex_vec):
        try:
            lengthFreqSex={}
            sexes=['Male','Female','Unsexed', 'Total']
            for sex in sexes:# make empty holder
                lengthFreq=[]
                for i in range(100):
                    lengthFreq.append(0)
                lengthFreqSex.update({sex:lengthFreq})
            for i in range(len(length_vec)):
                bin_ind=int(round(length_vec[i]))-1# 0 based indexing
                lengthFreqSex[sex_vec[i]][bin_ind]=lengthFreqSex[sex_vec[i]][bin_ind]+weight_vec[i]
                lengthFreqSex['Total'][bin_ind]=lengthFreqSex['Total'][bin_ind]+weight_vec[i]
            return  (True, lengthFreqSex)
        except:
            return (False, traceback.format_exception(*sys.exc_info()))
            print(traceback.format_exception(*sys.exc_info()))


    def loadAgeData(self, ageDict):

        number=1
        e=True
        try:
            query = self.db.dbQuery("SELECT measurement_value, specimen_id, sample_id, event_id FROM "+
                    self.db.bioSchema+".measurements WHERE "+ " ship="+self.ship+" AND survey="+self.survey+
                    " AND measurement_type='barcode'")
            for measurement_value, specimen_id, sample_id, event_id in query:
                if measurement_value in ageDict:
                    # check if age already in
                    query1 = self.db.dbQuery("SELECT measurement_value FROM "+self.db.bioSchema+".measurements WHERE ship="+
                            self.ship+" AND survey="+self.survey+" AND measurement_type='age' "+
                            "AND specimen_id="+specimen_id)
                    val=query1.first()[0]
                    if val is not None:
                        self.db.dbExec("UPDATE "+self.db.bioSchema+".measurements SET measurement_value='"+
                                str(ageDict[measurement_value]) + "' WHERE ship="+self.ship +
                                " AND survey="+self.survey+" AND measurement_type='age' "+ "AND specimen_id="+
                                specimen_id)
                    else:
                        self.db.dbExec("INSERT INTO "+self.db.bioSchema+".measurements (ship, survey, event_id, " +
                                "sample_id, specimen_id, measurement_type, measurement_value, device_id) "+
                                "VALUES ("+self.ship+", "+self.survey+", "+event_id+", "+sample_id+", "+specimen_id+
                                ",'age',"+str(ageDict[measurement_value])+",0)")
                    number += 1
        except Exception as e:
            print(e)

        return e



