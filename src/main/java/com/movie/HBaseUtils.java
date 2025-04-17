package com.movie;

import org.apache.hadoop.hbase.Cell;
import org.apache.hadoop.hbase.HColumnDescriptor;
import org.apache.hadoop.hbase.HTableDescriptor;
import org.apache.hadoop.hbase.TableName;
import org.apache.hadoop.hbase.client.*;
import org.apache.hadoop.hbase.filter.Filter;
import org.apache.hadoop.hbase.util.Bytes;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.*;

@Service
public class HBaseUtils {

    @Autowired
    private Admin hbaseAdmin;

    /**
     * 判断表是否存在
     *
     * @param tableName 表名
     * @return true/false
     */
    public boolean isExists(String tableName) {
        boolean tableExists = false;
        try {
            TableName table = TableName.valueOf(tableName);
            tableExists = hbaseAdmin.tableExists(table);
        } catch (IOException e) {
            e.printStackTrace();
        }
        return tableExists;
    }

    /**
     * 创建表
     * @param tableName 表名
     * @param columnFamily 列族
     * @return true/false
     */
    public boolean createTable(String tableName, List<String> columnFamily) {
        return createTable(tableName, columnFamily, null);
    }

    /**
     * 预分区创建表
     * @param tableName 表名
     * @param columnFamily 列族
     * @param keys 分区集合
     * @return true/false
     */
    public boolean createTable(String tableName, List<String> columnFamily, List<String> keys) {
        if (!isExists(tableName)) {
            try {
                TableName table = TableName.valueOf(tableName);
                HTableDescriptor desc = new HTableDescriptor(table);
                for (String cf : columnFamily) {
                    desc.addFamily(new HColumnDescriptor(cf));
                }
                if (keys == null) {
                    hbaseAdmin.createTable(desc);
                } else {
                    byte[][] splitKeys = getSplitKeys(keys);
                    hbaseAdmin.createTable(desc, splitKeys);
                }
                return true;
            } catch (IOException e) {
                e.printStackTrace();
            }
        } else {
            System.out.println(tableName + "is exists!!!");
            return false;
        }
        return false;
    }

    /**
     * 删除表
     *
     * @param tableName 表名
     */
    public void dropTable(String tableName) throws IOException {
        if (isExists(tableName)) {
            TableName table = TableName.valueOf(tableName);
            hbaseAdmin.disableTable(table);
            hbaseAdmin.deleteTable(table);
        }
    }

    /**
     * 插入数据（单条）
     * @param tableName 表名
     * @param rowKey rowKey
     * @param columnFamily 列族
     * @param column 列
     * @param value 值
     * @return true/false
     */
    public boolean putData(String tableName, String rowKey, String columnFamily, String column,
                           String value) {
        return putData(tableName, rowKey, columnFamily, Arrays.asList(column),
                Arrays.asList(value));
    }

    /**
     * 插入数据（批量）
     * @param tableName 表名
     * @param rowKey rowKey
     * @param columnFamily 列族
     * @param columns 列
     * @param values 值
     * @return true/false
     */
    public boolean putData(String tableName, String rowKey, String columnFamily,
                           List<String> columns, List<String> values) {
        try {
            Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
            Put put = new Put(Bytes.toBytes(rowKey));
            for (int i=0; i<columns.size(); i++) {
                put.addColumn(Bytes.toBytes(columnFamily), Bytes.toBytes(columns.get(i)),
                        Bytes.toBytes(values.get(i)));
            }
            table.put(put);
            table.close();
            return true;
        } catch (IOException e) {
            e.printStackTrace();
            return false;
        }
    }

    /**
     * 获取数据（全表数据）
     * @param tableName 表名
     * @return map
     */
    public List<Map<String, String>> getData(String tableName) {
        List<Map<String, String>> list = new ArrayList<>();
        try {
            Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
            Scan scan = new Scan();
            ResultScanner resultScanner = table.getScanner(scan);
            for(Result result : resultScanner) {
                HashMap<String, String> map = new HashMap<>();
                //rowkey
                String row = Bytes.toString(result.getRow());
                map.put("row", row);
                for (Cell cell : result.listCells()) {
                    //列族
                    String family = Bytes.toString(cell.getFamilyArray(),
                            cell.getFamilyOffset(), cell.getFamilyLength());
                    //列
                    String qualifier = Bytes.toString(cell.getQualifierArray(),
                            cell.getQualifierOffset(), cell.getQualifierLength());
                    //值
                    String data = Bytes.toString(cell.getValueArray(),
                            cell.getValueOffset(), cell.getValueLength());
                    map.put(family + ":" + qualifier, data);
                }
                list.add(map);
            }
            table.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return list;
    }

    /**
     * 获取数据（根据传入的filter）
     * @param tableName 表名
     * @param filter 过滤器
     * @return map
     */
    public List<Map<String, String>> getData(String tableName, Filter filter) {
        List<Map<String, String>> list = new ArrayList<>();
        try {
            Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
            Scan scan = new Scan();
            // 添加过滤器
            scan.setFilter(filter);
            ResultScanner resultScanner = table.getScanner(scan);
            for(Result result : resultScanner) {
                HashMap<String, String> map = new HashMap<>();
                //rowkey
                String row = Bytes.toString(result.getRow());
                map.put("row", row);
                for (Cell cell : result.listCells()) {
                    //列族
                    String family = Bytes.toString(cell.getFamilyArray(),
                        cell.getFamilyOffset(), cell.getFamilyLength());
                    //列
                    String qualifier = Bytes.toString(cell.getQualifierArray(),
                        cell.getQualifierOffset(), cell.getQualifierLength());
                    //值
                    String data = Bytes.toString(cell.getValueArray(),
                        cell.getValueOffset(), cell.getValueLength());
                    map.put(family + ":" + qualifier, data);
                }
                list.add(map);
            }
            table.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return list;
    }

    /**
     * 获取数据（根据rowkey）
     * @param tableName 表名
     * @param rowKey rowKey
     * @return map
     */
    public Map<String, String> getData(String tableName, String rowKey) {
        HashMap<String, String> map = new HashMap<>();
        try {
            Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
            Get get = new Get(Bytes.toBytes(rowKey));
            Result result = table.get(get);
            if (result != null && !result.isEmpty()) {
                for (Cell cell : result.listCells()) {
                    //列族
                    String family = Bytes.toString(cell.getFamilyArray(),
                            cell.getFamilyOffset(), cell.getFamilyLength());
                    //列
                    String qualifier = Bytes.toString(cell.getQualifierArray(),
                            cell.getQualifierOffset(), cell.getQualifierLength());
                    //值
                    String data = Bytes.toString(cell.getValueArray(),
                            cell.getValueOffset(), cell.getValueLength());
                    map.put(family + ":" + qualifier, data);
                }
            }
            table.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return map;
    }

    /**
     * 获取数据（根据rowkey，列族，列）
     * @param tableName 表名
     * @param rowKey rowKey
     * @param columnFamily 列族
     * @param columnQualifier 列
     * @return map
     */
    public String getData(String tableName, String rowKey, String columnFamily,
                          String columnQualifier) {
        String data = "";
        try {
            Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
            Get get = new Get(Bytes.toBytes(rowKey));
            get.addColumn(Bytes.toBytes(columnFamily), Bytes.toBytes(columnQualifier));
            Result result = table.get(get);
            if (result != null && !result.isEmpty()) {
                Cell cell = result.listCells().get(0);
                data = Bytes.toString(cell.getValueArray(), cell.getValueOffset(),
                        cell.getValueLength());
            }
            table.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return data;
    }

    /**
     * 删除数据（根据rowkey）
     * @param tableName 表名
     * @param rowKey rowKey
     */
    public void deleteData(String tableName, String rowKey) throws IOException{
        Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
        Delete delete = new Delete(Bytes.toBytes(rowKey));
        table.delete(delete);
        table.close();
    }

    /**
     * 删除数据（根据rowkey，列族）
     * @param tableName 表名
     * @param rowKey rowKey
     * @param columnFamily 列族
     */
    public void deleteData(String tableName, String rowKey, String columnFamily)
            throws IOException{
        Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
        Delete delete = new Delete(Bytes.toBytes(rowKey));
        delete.addFamily(columnFamily.getBytes());
        table.delete(delete);
        table.close();
    }

    /**
     * 删除数据（根据rowkey，列族）
     * @param tableName 表名
     * @param rowKey rowKey
     * @param columnFamily 列族
     * @param column 列
     */
    public void deleteData(String tableName, String rowKey, String columnFamily, String column)
            throws IOException{
        Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
        Delete delete = new Delete(Bytes.toBytes(rowKey));
        delete.addColumn(columnFamily.getBytes(), column.getBytes());
        table.delete(delete);
        table.close();
    }

    /**
     * 删除数据（多行）
     * @param tableName 表名
     * @param rowKeys rowKey集合
     */
    public void deleteData(String tableName, List<String> rowKeys) throws IOException{
        Table table = hbaseAdmin.getConnection().getTable(TableName.valueOf(tableName));
        List<Delete> deleteList = new ArrayList<>();
        for(String row : rowKeys){
            Delete delete = new Delete(Bytes.toBytes(row));
            deleteList.add(delete);
        }
        table.delete(deleteList);
        table.close();
    }

    /**
     * 分区【10, 20, 30】 -> ( ,10] (10,20] (20,30] (30, )
     * @param keys 分区集合[10, 20, 30]
     * @return byte二维数组
     */
    private byte[][] getSplitKeys(List<String> keys) {
        byte[][] splitKeys = new byte[keys.size()][];
        TreeSet<byte[]> rows = new TreeSet<>(Bytes.BYTES_COMPARATOR);
        for(String key : keys) {
            rows.add(Bytes.toBytes(key));
        }
        int i = 0;
        for (byte[] row : rows) {
            splitKeys[i] = row;
            i ++;
        }
        return splitKeys;
    }
}