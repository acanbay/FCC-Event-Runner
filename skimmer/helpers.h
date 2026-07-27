#ifndef FCC_EVENT_RUNNER_SKIMMER_HELPERS_H
#define FCC_EVENT_RUNNER_SKIMMER_HELPERS_H

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

#include "ROOT/RVec.hxx"
#include "edm4hep/EventHeaderCollection.h"
#include "edm4hep/ParticleIDCollection.h"
#include "edm4hep/ReconstructedParticleCollection.h"
#include "edm4hep/utils/kinematics.h"

namespace FCCEventRunnerSkim {

inline float absEta(const edm4hep::ReconstructedParticle &particle) {
  const auto momentum = particle.getMomentum();
  const auto pt = std::hypot(momentum.x, momentum.y);
  if (pt == 0.f) {
    return std::numeric_limits<float>::infinity();
  }
  return std::abs(std::asinh(momentum.z / pt));
}

inline edm4hep::ReconstructedParticleCollection
sortByPt(const edm4hep::ReconstructedParticleCollection &particles) {
  std::vector<edm4hep::ReconstructedParticle> sortedParticles;
  sortedParticles.reserve(particles.size());
  for (const auto &particle : particles) {
    sortedParticles.emplace_back(particle);
  }
  std::sort(
      sortedParticles.begin(), sortedParticles.end(),
      [](const auto &left, const auto &right) {
        return edm4hep::utils::pt(left) > edm4hep::utils::pt(right);
      });

  edm4hep::ReconstructedParticleCollection result;
  result.setSubsetCollection();
  for (const auto &particle : sortedParticles) {
    result.push_back(particle);
  }
  return result;
}

inline edm4hep::ReconstructedParticleCollection
select(const edm4hep::ReconstructedParticleCollection &particles,
       const float ptMin, const float absEtaMin, const float absEtaMax) {
  edm4hep::ReconstructedParticleCollection selected;
  selected.setSubsetCollection();

  for (const auto &particle : particles) {
    const auto pt = edm4hep::utils::pt(particle);
    const auto eta = absEta(particle);
    if (pt >= ptMin && eta >= absEtaMin && eta < absEtaMax) {
      selected.push_back(particle);
    }
  }
  return sortByPt(selected);
}

inline bool tagged(const edm4hep::ParticleID &tag, const unsigned int bit) {
  const auto parameters = tag.getParameters();
  if (parameters.empty()) {
    return false;
  }
  const auto mask = static_cast<std::uint32_t>(
      std::llround(static_cast<double>(parameters[0])));
  return (mask & (std::uint32_t{1} << bit)) != 0;
}

inline edm4hep::ReconstructedParticleCollection
selectBJets(const edm4hep::ReconstructedParticleCollection &jets,
            const edm4hep::ParticleIDCollection &tags, const unsigned int bit,
            const float ptMin, const float centralAbsEtaMax) {
  if (jets.size() != tags.size()) {
    throw std::runtime_error(
        "Jet and heavy-flavour tag collections have different sizes.");
  }

  edm4hep::ReconstructedParticleCollection selected;
  selected.setSubsetCollection();
  for (std::size_t index = 0; index < jets.size(); ++index) {
    const auto jet = jets[index];
    if (edm4hep::utils::pt(jet) >= ptMin &&
        absEta(jet) < centralAbsEtaMax && tagged(tags[index], bit)) {
      selected.push_back(jet);
    }
  }
  return sortByPt(selected);
}

inline edm4hep::ReconstructedParticleCollection
merge(const edm4hep::ReconstructedParticleCollection &first,
      const edm4hep::ReconstructedParticleCollection &second) {
  edm4hep::ReconstructedParticleCollection result;
  result.setSubsetCollection();
  for (const auto &particle : first) {
    result.push_back(particle);
  }
  for (const auto &particle : second) {
    result.push_back(particle);
  }
  return sortByPt(result);
}

inline ROOT::VecOps::RVec<float>
pt(const edm4hep::ReconstructedParticleCollection &particles) {
  ROOT::VecOps::RVec<float> result;
  result.reserve(particles.size());
  for (const auto &particle : particles) {
    result.push_back(edm4hep::utils::pt(particle));
  }
  return result;
}

inline ROOT::VecOps::RVec<float>
eta(const edm4hep::ReconstructedParticleCollection &particles) {
  ROOT::VecOps::RVec<float> result;
  result.reserve(particles.size());
  for (const auto &particle : particles) {
    const auto momentum = particle.getMomentum();
    const auto transverseMomentum = std::hypot(momentum.x, momentum.y);
    result.push_back(
        transverseMomentum == 0.f
            ? std::copysign(std::numeric_limits<float>::infinity(), momentum.z)
            : std::asinh(momentum.z / transverseMomentum));
  }
  return result;
}

inline ROOT::VecOps::RVec<float>
phi(const edm4hep::ReconstructedParticleCollection &particles) {
  ROOT::VecOps::RVec<float> result;
  result.reserve(particles.size());
  for (const auto &particle : particles) {
    const auto momentum = particle.getMomentum();
    result.push_back(std::atan2(momentum.y, momentum.x));
  }
  return result;
}

inline ROOT::VecOps::RVec<float>
mass(const edm4hep::ReconstructedParticleCollection &particles) {
  ROOT::VecOps::RVec<float> result;
  result.reserve(particles.size());
  for (const auto &particle : particles) {
    result.push_back(particle.getMass());
  }
  return result;
}

inline ROOT::VecOps::RVec<float>
charge(const edm4hep::ReconstructedParticleCollection &particles) {
  ROOT::VecOps::RVec<float> result;
  result.reserve(particles.size());
  for (const auto &particle : particles) {
    result.push_back(particle.getCharge());
  }
  return result;
}

inline float met(
    const edm4hep::ReconstructedParticleCollection &missingMomentum) {
  if (missingMomentum.empty()) {
    return 0.f;
  }
  return edm4hep::utils::pt(missingMomentum[0]);
}

inline float mll(const edm4hep::ReconstructedParticleCollection &leptons) {
  if (leptons.size() != 2) {
    return -1.f;
  }
  const auto first = leptons[0];
  const auto second = leptons[1];
  const auto p1 = first.getMomentum();
  const auto p2 = second.getMomentum();
  const auto energy = first.getEnergy() + second.getEnergy();
  const auto px = p1.x + p2.x;
  const auto py = p1.y + p2.y;
  const auto pz = p1.z + p2.z;
  const auto massSquared =
      energy * energy - px * px - py * py - pz * pz;
  return std::sqrt(std::max(0.f, massSquared));
}

inline float
chargeProduct(const edm4hep::ReconstructedParticleCollection &leptons) {
  if (leptons.size() != 2) {
    return 0.f;
  }
  return leptons[0].getCharge() * leptons[1].getCharge();
}

inline double eventWeight(const edm4hep::EventHeaderCollection &headers) {
  if (headers.empty()) {
    return 1.0;
  }
  return headers[0].getWeight();
}

} // namespace FCCEventRunnerSkim

#endif
