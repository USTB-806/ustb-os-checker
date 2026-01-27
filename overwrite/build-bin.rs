use std::{
    fs::{File, read_dir}, 
    io::{Result, Write},
    path::Path,
};

static TARGET_PATH: &str = "../user/build/";

fn main() {
    println!("cargo:rerun-if-changed=../user/c/apps/");
    println!("cargo:rerun-if-changed=../user/rust/src/");
    println!("cargo:rerun-if-changed={}", TARGET_PATH);
    insert_app_data().unwrap();
}

/// get app data and build linker
fn insert_app_data() -> Result<()> {
    let mut f = File::create("src/link_app.S").unwrap();
    
    let target_path = Path::new(TARGET_PATH);
    if !target_path.exists() {
        println!("cargo:warning=User app target directory not found: {}", TARGET_PATH);
        writeln!(f, r#"
    .align 3
    .section .data
    .global _num_app
_num_app:
    .quad 0"#)?;
        return Ok(());
    }

    let mut apps: Vec<_> = read_dir(TARGET_PATH)
        .unwrap()
        .into_iter()
        .filter_map(|dir_entry| {
            let entry = dir_entry.unwrap();
            let path = entry.path();
            if path.is_dir() {
                return None;
            }
            let name = entry.file_name().into_string().unwrap();
            if path.extension().is_none() && !name.starts_with('.') {
                Some(name)
            } else {
                None
            }
        })
        .collect();

    apps.sort();

    writeln!(
        f,
        r#"
    .align 3
    .section .data
    .global _num_app
_num_app:
    .quad {}"#,
        apps.len()
    )?;

    for i in 0..apps.len() {
        writeln!(f, r#"    .quad app_{}_start"#, i)?;
    }
    writeln!(f, r#"    .quad app_{}_end"#, apps.len() - 1)?;

    for (idx, app) in apps.iter().enumerate() {
        println!("app_{}: {}", idx, app);
        let app_path = target_path.join(app).canonicalize().unwrap();
        writeln!(
            f,
            r#"
    .section .data
    .global app_{0}_start
    .global app_{0}_end
    .align 3
app_{0}_start:
    .incbin "{1}"
app_{0}_end:"#,
            idx, app_path.to_str().unwrap()
        )?;
    }
    Ok(())
}
