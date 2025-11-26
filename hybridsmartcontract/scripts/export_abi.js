import fs from "fs";
import path from "path";

async function main() {
  // 1. Tìm file artifact đã compile
  const artifactPath = path.join(
    new URL('.', import.meta.url).pathname,
    "../artifacts/contracts/DCALedger.sol/DCALedger.json"
  );

    if (!fs.existsSync(artifactPath)) {
        console.error("Lỗi: Chưa tìm thấy file compile. Hãy chạy 'npx hardhat compile' trước.");
        process.exit(1);
    }

    // 2. Đọc nội dung
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));

    // 3. Lọc lấy đúng 2 thứ Python cần
    const dataForPython = {
        abi: artifact.abi,
        bytecode: artifact.bytecode
    };

  // 4. Ghi ra file json
  const outputPath = path.join(new URL('.', import.meta.url).pathname, "../compiled_contract.json");
  fs.writeFileSync(outputPath, JSON.stringify(dataForPython, null, 2));

    console.log(`>> Đã xuất file thành công: ${outputPath}`);
    console.log(">> Copy file này sang source Python.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
