Main:numberOfEvents = @LHE_EVENTS@

Random:setSeed = on
Random:seed = @PYTHIA_SEED@

Beams:frameType = 4
Beams:setProductionScalesFromLHEF = off
Beams:LHEF = @LHE_FILE@

JetMatching:merge = on
JetMatching:scheme = 1
JetMatching:setMad = off

JetMatching:qCut = 45.0
JetMatching:nQmatch = 4
JetMatching:clFact = 1.0
JetMatching:nJetMax = 2
JetMatching:doShowerKt = off

JetMatching:coneRadius = 1.0
JetMatching:etaJetMax = 6.0