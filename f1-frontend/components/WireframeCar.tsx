"use client";

import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { MeshSurfaceSampler } from "three/examples/jsm/math/MeshSurfaceSampler.js";

// Builds a stylized, low-poly F1-silhouette car entirely from primitive
// geometry — no imported mesh, no team livery, no licensing ambiguity.
// The shape is deliberately abstracted (a "data construct"), not a replica.
function buildCarGroup(): THREE.Group {
  const group = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({
    color: 0x00e5ff,
    wireframe: true,
    transparent: true,
    opacity: 0,
  });

  // Body: extruded side-profile silhouette (nose low, cockpit bump, rear)
  const profile = new THREE.Shape();
  profile.moveTo(-2.6, 0.05);
  profile.lineTo(-2.3, 0.12);
  profile.quadraticCurveTo(-1.6, 0.22, -1.0, 0.3);
  profile.quadraticCurveTo(-0.6, 0.55, -0.2, 0.58);
  profile.quadraticCurveTo(0.2, 0.6, 0.5, 0.35);
  profile.quadraticCurveTo(1.2, 0.28, 2.0, 0.2);
  profile.lineTo(2.5, 0.12);
  profile.lineTo(2.5, 0.0);
  profile.lineTo(-2.6, 0.0);
  profile.lineTo(-2.6, 0.05);

  const body = new THREE.Mesh(
    new THREE.ExtrudeGeometry(profile, { depth: 0.9, bevelEnabled: false }),
    mat
  );
  body.position.set(0, 0, -0.45);
  group.add(body);

  // Front + rear wings
  const frontWing = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.06, 1.3), mat);
  frontWing.position.set(-2.55, 0.06, 0);
  group.add(frontWing);

  const rearWing = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.35, 1.1), mat);
  rearWing.position.set(2.55, 0.35, 0);
  group.add(rearWing);
  const rearWingPlane = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.05, 1.1), mat);
  rearWingPlane.position.set(2.55, 0.5, 0);
  group.add(rearWingPlane);

  // Halo (cockpit protection loop) — instantly reads as "F1" in silhouette
  const halo = new THREE.Mesh(
    new THREE.TorusGeometry(0.32, 0.02, 6, 24, Math.PI),
    mat
  );
  halo.rotation.set(0, Math.PI / 2, 0);
  halo.position.set(-0.25, 0.75, 0);
  group.add(halo);

  // Wheels — 4 open cylinders
  const wheelPositions: [number, number][] = [
    [-1.75, 0.65],
    [-1.75, -0.65],
    [1.65, 0.7],
    [1.65, -0.7],
  ];
  wheelPositions.forEach(([x, z]) => {
    const wheel = new THREE.Mesh(
      new THREE.CylinderGeometry(0.35, 0.35, 0.28, 16, 1, true),
      mat
    );
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(x, 0.35, z);
    group.add(wheel);
  });

  return group;
}

const PARTICLE_COUNT = 2200;

// Sample target points across every mesh's surface in world space.
function sampleTargets(carGroup: THREE.Group): Float32Array {
  const meshes: THREE.Mesh[] = [];
  carGroup.traverse((c) => {
    if ((c as THREE.Mesh).isMesh) meshes.push(c as THREE.Mesh);
  });

  const perMesh = Math.floor(PARTICLE_COUNT / meshes.length);
  const pts: Float32Array = new Float32Array(perMesh * meshes.length * 3);
  let i = 0;

  meshes.forEach((mesh) => {
    mesh.updateMatrixWorld(true);
    const sampler = new MeshSurfaceSampler(mesh).build();
    const p = new THREE.Vector3();
    for (let s = 0; s < perMesh; s++) {
      sampler.sample(p);
      p.applyMatrix4(mesh.matrixWorld);
      pts[i++] = p.x;
      pts[i++] = p.y;
      pts[i++] = p.z;
    }
  });
  return pts;
}

// Scatter each particle to a random point on a shell around the car.
function computeOrigins(targets: Float32Array) {
  const count = targets.length / 3;
  const origins = new Float32Array(targets.length);
  for (let i = 0; i < count; i++) {
    const r = 4.5 + Math.random() * 3;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    origins[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    origins[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) + 0.4;
    origins[i * 3 + 2] = r * Math.cos(phi);
  }
  return { positions: origins.slice(), origins };
}

export default function WireframeCar() {
  const groupRef = useRef<THREE.Group>(null);
  const pointsRef = useRef<THREE.Points>(null);
  const startTime = useRef<number | null>(null);

  const carGroup = useMemo(() => buildCarGroup(), []);

  // Both of these call Math.random() — MeshSurfaceSampler.sample() internally,
  // computeOrigins() directly — so neither belongs in useMemo, which React 19
  // requires to be pure and replayable. A useState lazy initializer runs
  // exactly once per mount and its result is safe to read during render
  // (unlike a ref, which isn't). Runtime behavior is unchanged: both were
  // already computed exactly once.
  const [{ targets, positions, origins }] = useState(() => {
    const sampled = sampleTargets(carGroup);
    return { targets: sampled, ...computeOrigins(sampled) };
  });

  function easeOutCubic(t: number) {
    return 1 - Math.pow(1 - t, 3);
  }

  useFrame((state) => {
    if (startTime.current === null) startTime.current = state.clock.elapsedTime;
    const elapsed = state.clock.elapsedTime - startTime.current;
    const duration = 2.4;
    const rawT = Math.min(elapsed / duration, 1);
    const t = easeOutCubic(rawT);

    if (pointsRef.current) {
      const attr = pointsRef.current.geometry.getAttribute(
        "position"
      ) as THREE.BufferAttribute;
      const arr = attr.array as Float32Array;
      for (let i = 0; i < arr.length; i++) {
        arr[i] = origins[i] + (targets[i] - origins[i]) * t;
      }
      attr.needsUpdate = true;

      const mat = pointsRef.current.material as THREE.PointsMaterial;
      mat.opacity = 0.55 + 0.45 * (1 - rawT); // brighter while assembling
    }

    if (groupRef.current) {
      carGroup.traverse((c) => {
        const mesh = c as THREE.Mesh;
        if (mesh.isMesh) {
          (mesh.material as THREE.MeshBasicMaterial).opacity = Math.max(
            0,
            (rawT - 0.6) / 0.4
          );
        }
      });
    }
  });

  return (
    <group>
      <primitive ref={groupRef} object={carGroup} />
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[positions, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.028}
          color={0x00e5ff}
          transparent
          opacity={1}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>
    </group>
  );
}
