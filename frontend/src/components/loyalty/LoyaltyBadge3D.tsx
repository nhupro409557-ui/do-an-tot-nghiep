import React, { useEffect, useRef } from 'react';
import p5 from 'p5';

// Định nghĩa các hạng thành viên
export type Tier = 'Member' | 'Silver' | 'Gold' | 'Diamond';

interface LoyaltyBadgeProps {
  tier: string;
  size?: number; // Kích thước của canvas
}

export const LoyaltyBadge3D: React.FC<LoyaltyBadgeProps> = ({ tier, size = 200 }) => {
  const renderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!renderRef.current) return;

    // Định nghĩa logic của p5.js (Generative Art)
    const sketch = (p: p5) => {
      p.setup = () => {
        // Khởi tạo canvas với mode WEBGL để vẽ 3D
        p.createCanvas(size, size, p.WEBGL);
        p.noStroke(); // Bỏ viền để khối 3D mượt hơn
      };

      p.draw = () => {
        // Nền trong suốt
        p.clear();
        
        // --- Thiết lập ánh sáng (Lighting) ---
        p.ambientLight(60, 60, 60);
        // Đèn rọi từ góc trên bên phải
        p.pointLight(255, 255, 255, size / 2, -size / 2, size);
        p.directionalLight(255, 255, 255, 0.25, 0.25, -1);

        // --- Chuyển động xoay tự động ---
        p.rotateX(p.frameCount * 0.01);
        p.rotateY(p.frameCount * 0.015);

        // --- Cấu hình vật liệu và hình khối theo Hạng (Tier) ---
        switch (tier) {
          case 'Member':
            // Hạng thường: Khối lập phương bo tròn, màu đồng/xám
            p.specularMaterial(180, 150, 130);
            p.shininess(10);
            p.box(size * 0.35);
            break;

          case 'Silver':
            // Hạng Bạc: Hình xuyến (Torus), màu bạc lấp lánh
            p.specularMaterial(210, 210, 210);
            p.shininess(30);
            p.torus(size * 0.25, size * 0.1);
            break;

          case 'Gold':
            // Hạng Vàng: Khối cầu, ánh vàng kim rực rỡ
            p.specularMaterial(255, 215, 0);
            p.shininess(50);
            p.sphere(size * 0.3, 24, 24);
            // Thêm một vòng đai bay quanh
            p.rotateX(p.frameCount * 0.02);
            p.torus(size * 0.4, size * 0.02);
            break;

          case 'Diamond':
            // Hạng Kim Cương: Khối đa diện phức tạp (Cone/Cylinder kết hợp), phát sáng xanh/tím
            p.ambientLight(100, 150, 255);
            p.specularMaterial(150, 200, 255);
            p.shininess(100);
            
            // Vẽ 2 hình nón úp vào nhau tạo thành hình viên kim cương
            p.push();
            p.translate(0, -size * 0.15);
            p.cone(size * 0.3, size * 0.3, 6, 1);
            p.pop();
            p.push();
            p.translate(0, size * 0.15);
            p.rotateX(p.PI);
            p.cone(size * 0.3, size * 0.4, 6, 1);
            p.pop();
            break;
        }
      };
    };

    // Khởi tạo instance của p5
    const p5Instance = new p5(sketch, renderRef.current);

    // Dọn dẹp (Cleanup) khi component bị unmount để tránh rò rỉ bộ nhớ
    return () => {
      p5Instance.remove();
    };
  }, [tier, size]); // Render lại sketch nếu tier hoặc size thay đổi

  return (
    <div 
      ref={renderRef} 
      className="flex justify-center items-center drop-shadow-2xl"
    />
  );
};
