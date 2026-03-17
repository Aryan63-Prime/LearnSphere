/**
 * LearnSphere AI Avatar
 * A generative digital persona using Three.js
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export class LearnSphereAvatar {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        // Scene Setup
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, this.container.offsetWidth / this.container.offsetHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

        this.renderer.setSize(this.container.offsetWidth || 400, this.container.offsetHeight || 300);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        this.camera.position.z = 6;

        // Core Objects
        this.robot = null;
        this.loadedModel = null;
        this.particles = null; // Keep particles for addParticles method
        this.clock = new THREE.Clock();

        // Loaders
        this.loader = new GLTFLoader();

        // Lights
        const light = new THREE.DirectionalLight(0xffffff, 1);
        light.position.set(5, 10, 7);
        this.scene.add(light);
        this.scene.add(new THREE.AmbientLight(0xffffff, 0.6));

        // Add subtle floating particles
        this.addParticles();

        this.initFullBodyAvatar();
        this.animate();

        // Resize Observer
        const ro = new ResizeObserver(() => this.onResize());
        ro.observe(this.container);

        window.addEventListener('resize', () => this.onResize());
    }

    initFullBodyAvatar() {
        if (this.robot) this.scene.remove(this.robot);
        this.robot = new THREE.Group();
        this.scene.add(this.robot);

        // Materials
        const skinMat = new THREE.MeshPhongMaterial({ color: 0xffccaa, flatShading: true });
        const shirtMat = new THREE.MeshPhongMaterial({ color: 0x6366f1, flatShading: true }); // Indigo shirt
        const pantsMat = new THREE.MeshPhongMaterial({ color: 0x1f2937, flatShading: true }); // Dark pants

        // 1. Torso
        const torsoGeo = new THREE.BoxGeometry(1, 1.5, 0.6);
        this.torso = new THREE.Mesh(torsoGeo, shirtMat);
        this.torso.position.y = 0.75;
        this.robot.add(this.torso);

        // 2. Head
        const headGeo = new THREE.BoxGeometry(0.8, 0.8, 0.8);
        this.head = new THREE.Mesh(headGeo, skinMat);
        this.head.position.y = 1.2;
        this.torso.add(this.head);

        // Eyes
        const eyeGeo = new THREE.BoxGeometry(0.15, 0.05, 0.05);
        const eyeMat = new THREE.MeshBasicMaterial({ color: 0x000000 });

        const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
        leftEye.position.set(-0.2, 0.1, 0.41);
        this.head.add(leftEye);

        const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
        rightEye.position.set(0.2, 0.1, 0.41);
        this.head.add(rightEye);

        // 3. Arms (Pivoted at shoulders)
        const armGeo = new THREE.BoxGeometry(0.3, 1.2, 0.3);

        // Left Arm Group (for pivot)
        this.leftArm = new THREE.Group();
        this.leftArm.position.set(-0.65, 0.6, 0);
        this.torso.add(this.leftArm);
        const lArmMesh = new THREE.Mesh(armGeo, skinMat);
        lArmMesh.position.y = -0.4; // Offset so 0,0 is shoulder
        this.leftArm.add(lArmMesh); // Add mesh to pivot group

        // Right Arm Group
        this.rightArm = new THREE.Group();
        this.rightArm.position.set(0.65, 0.6, 0);
        this.torso.add(this.rightArm);
        const rArmMesh = new THREE.Mesh(armGeo, skinMat);
        rArmMesh.position.y = -0.4;
        this.rightArm.add(rArmMesh);

        // 4. Legs
        const legGeo = new THREE.BoxGeometry(0.35, 1.5, 0.35);

        this.leftLeg = new THREE.Mesh(legGeo, pantsMat);
        this.leftLeg.position.set(-0.25, -0.75, 0);
        this.torso.add(this.leftLeg);

        this.rightLeg = new THREE.Mesh(legGeo, pantsMat);
        this.rightLeg.position.set(0.25, -0.75, 0);
        this.torso.add(this.rightLeg);

        // 5. Floor/Stage
        const floorGeo = new THREE.CylinderGeometry(3, 3, 0.2, 32);
        const floorMat = new THREE.MeshLambertMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.1
        });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.position.y = -0.1;
        this.robot.add(floor);

        // Position entire robot
        this.robot.position.y = -1.5; // Move down to fit in view
    }

    addParticles() {
        const pCount = 200;
        const pGeometry = new THREE.BufferGeometry();
        const pPositions = new Float32Array(pCount * 3);

        for (let i = 0; i < pCount * 3; i++) {
            pPositions[i] = (Math.random() - 0.5) * 15;
        }

        pGeometry.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
        const pMaterial = new THREE.PointsMaterial({
            color: 0xa78bfa,
            size: 0.05,
            transparent: true,
            opacity: 0.4
        });

        this.particles = new THREE.Points(pGeometry, pMaterial);
        this.scene.add(this.particles);
    }

    loadModel(url) {
        if (!this.loader) return;

        this.loader.load(url, (gltf) => {
            if (this.robot) {
                this.scene.remove(this.robot);
                this.robot = null;
            }
            if (this.loadedModel) this.scene.remove(this.loadedModel);

            this.loadedModel = gltf.scene;
            this.scene.add(this.loadedModel);

            // Auto-center and scale
            const box = new THREE.Box3().setFromObject(this.loadedModel);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());

            // Reset position to center
            this.loadedModel.position.x += (this.loadedModel.position.x - center.x);
            this.loadedModel.position.y += (this.loadedModel.position.y - center.y);
            this.loadedModel.position.z += (this.loadedModel.position.z - center.z);

            // Scale to fit height of ~4 units
            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = 4 / maxDim;
            this.loadedModel.scale.set(scale, scale, scale);

            console.log("Custom model loaded and scaled:", scale);
        }, undefined, (error) => {
            console.error('An error happened loading GLB:', error);
            alert("Failed to load model. Ensure it is a valid .glb file.");
        });
    }

    onResize() {
        if (!this.container) return;
        this.camera.aspect = this.container.offsetWidth / this.container.offsetHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.offsetWidth, this.container.offsetHeight);
    }

    update(volume = 0) {
        const v = Math.min(1, volume / 100);
        const time = Date.now() * 0.005;

        // 1. Custom Model Animation
        if (this.loadedModel) {
            // ... (existing custom model logic logic if needed, or simple pulse)
            const baseScale = this.loadedModel.originalScale || this.loadedModel.scale.x;
            if (!this.loadedModel.originalScale) this.loadedModel.originalScale = baseScale;

            // Simple talk pulse
            const target = baseScale + (v * 0.05 * baseScale);
            this.loadedModel.scale.setScalar(THREE.MathUtils.lerp(this.loadedModel.scale.x, target, 0.3));
            return;
        }

        // 2. Full Body Procedural Animation
        if (this.robot) {
            // Idle Breath
            const breath = Math.sin(time * 0.5) * 0.02;
            this.torso.position.y = 0.75 + breath;

            // Talking Gesture (Arms)
            if (v > 0.1) {
                // Active talking gestures
                this.rightArm.rotation.z = Math.cos(time * 2) * 0.5 - 0.5; // Wave arm
                this.leftArm.rotation.z = Math.sin(time * 2) * 0.2 + 0.2;

                // Head bob
                this.head.rotation.x = Math.sin(time * 4) * 0.1;
                this.head.rotation.y = Math.sin(time * 2) * 0.1;
            } else {
                // Return to idle
                this.rightArm.rotation.z = THREE.MathUtils.lerp(this.rightArm.rotation.z, 0, 0.1);
                this.leftArm.rotation.z = THREE.MathUtils.lerp(this.leftArm.rotation.z, 0, 0.1);
                this.head.rotation.x = THREE.MathUtils.lerp(this.head.rotation.x, 0, 0.1);
                this.head.rotation.y = THREE.MathUtils.lerp(this.head.rotation.y, 0, 0.1);
            }
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.renderer.render(this.scene, this.camera);
    }
}
